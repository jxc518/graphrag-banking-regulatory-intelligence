from copy import deepcopy


def validate_request_scoped_matrix(
    matrix,
    sources,
    expected_banks,
    expected_period,
):
    rows = matrix.get("rows")

    if not isinstance(rows, list):
        raise ValueError(
            "Matrix rows must be a list"
        )

    expected = set(expected_banks)

    actual = {
        row.get("bank")
        for row in rows
    }

    if (
        len(rows) != len(expected)
        or actual != expected
    ):
        raise ValueError(
            "Matrix banks do not match request scope"
        )

    by_id = {
        source["source_id"]: source
        for source in sources
    }

    quote_errors = []

    for row in rows:

        evidence = row.get("evidence")

        if not isinstance(evidence, list):
            continue

        for number, item in enumerate(
            evidence,
            1,
        ):

            if not isinstance(item, dict):
                raise ValueError(
                    "Evidence entries must be objects"
                )

            source = by_id.get(
                item.get("source_id")
            )

            quote = item.get("quote")

            label = (
                f"{row.get('bank')} "
                f"evidence[{number}] "
                f"{item.get('source_id')}"
            )

            if source is None:
                quote_errors.append(
                    label + ": unknown source"
                )

            elif (
                source["bank"]
                != row.get("bank")
            ):
                quote_errors.append(
                    label
                    + ": cross-bank attribution"
                )

            elif (
                not isinstance(quote, str)
                or not quote.strip()
            ):
                quote_errors.append(
                    label
                    + ": empty or invalid quote"
                )

            elif quote not in source["text"]:
                quote_errors.append(
                    label
                    + ": not an exact source substring"
                )

    if quote_errors:
        raise ValueError(
            "Evidence quote validation failed: "
            + "; ".join(quote_errors)
        )

    for row in rows:

        for field in (
            "metric",
            "limitation",
        ):
            if not isinstance(
                row.get(field),
                str,
            ):
                raise ValueError(
                    f"Missing matrix field {field}"
                    
                )

        if (
            (expected_period is not None and row.get("period") != expected_period)
            or row.get("status")
            not in {
                "supported",
                "missing_evidence",
            }
        ):
            raise ValueError(
                "Invalid period/status"
            )

        for field in (
            "value",
            "unit",
            "scope",
        ):
            if (
                field not in row
                or (
                    row[field] is not None
                    and not isinstance(
                        row[field],
                        str,
                    )
                )
            ):
                raise ValueError(
                    f"Invalid {field}"
                )

        evidence = row.get("evidence")

        if (
            not isinstance(evidence, list)
            or len(evidence) > 4
        ):
            raise ValueError(
                "Invalid evidence list"
            )

        if (
            row["status"] == "supported"
            and (
                not evidence
                or not all(
                    row.get(field)
                    for field in (
                        "value",
                        "unit",
                        "scope",
                    )
                )
            )
        ):
            raise ValueError(
                "Supported row lacks "
                "required fields"
            )

        for item in evidence:

            source = by_id.get(
                item.get("source_id")
            )

            quote = item.get("quote")

            if (
                source is None
                or source["bank"]
                != row["bank"]
                or not isinstance(
                    quote,
                    str,
                )
                or not quote.strip()
                or quote
                not in source["text"]
            ):
                raise ValueError(
                    "Invalid quote or "
                    "cross-bank attribution"
                )

    return rows

# ============================================================
# STEP06 SERVING-LAYER RUNTIME WIRING
# ============================================================

from contextvars import ContextVar
import inspect


_EXPECTED_BANKS = ContextVar(
    "step06_expected_banks",
    default=None,
)


_EXPECTED_PERIOD = ContextVar(
    "_EXPECTED_PERIOD",
    default=None,
)


def _resolve_target_period(query):
    """
    Resolve the explicit quarter requested by this API request.
    """
    from GraphRAG_Phase3_Step06_API_SERVICE_06_query_scope import (
        resolve_target_period,
    )

    return resolve_target_period(query)

def _resolve_target_banks(query):
    """
    Reuse the already validated Step06 query-scope resolver.
    """

    from GraphRAG_Phase3_Step06_API_SERVICE_06_query_scope import (
        resolve_target_banks,
    )

    return resolve_target_banks(query)


def _set_request_scope(query):
    """
    Set request-local expected bank scope.
    """

    banks = _resolve_target_banks(query)

    token = _EXPECTED_BANKS.set(
        tuple(banks)
    )

    return banks, token


def _reset_request_scope(token):
    """
    Restore the previous ContextVar value.
    """

    _EXPECTED_BANKS.reset(token)


def _current_expected_banks():
    banks = _EXPECTED_BANKS.get()

    if not banks:
        raise RuntimeError(
            "Request-scoped bank contract "
            "was not initialized"
        )

    return list(banks)


def install(runtime_module):
    """
    Install request-scoped matrix validation into the
    live Step06 serving runtime.

    Important:
    - Does NOT modify frozen Phase2 source files.
    - Does NOT modify Step04 source files.
    - Uses ContextVar for request-local concurrency safety.
    """

    if getattr(
        runtime_module,
        "_step06_scope_contract_installed",
        False,
    ):
        return runtime_module

    original_bootstrap = (
        runtime_module.runtime_bootstrap_node
    )

    original_guard = (
        runtime_module.deterministic_guard_node
    )

    original_revalidation = getattr(
        runtime_module,
        "deterministic_revalidation_node",
        None,
    )

    validator_state = {
        "installed": False,
        "original_validate_matrix": None,
    }

    def install_validator_binding():
        """
        Bootstrap must run first because _base()
        is populated during runtime initialization.
        """

        if validator_state["installed"]:
            return

        base = runtime_module._base()

        original_validate_matrix = (
            base.validate_matrix
        )

        validator_state[
            "original_validate_matrix"
        ] = original_validate_matrix

        def scoped_validate_matrix(
            matrix,
            sources,
        ):
            expected_banks = (
                _current_expected_banks()
            )


            expected_period = _EXPECTED_PERIOD.get()
            return (
                validate_request_scoped_matrix(
                    matrix,
                    sources,
                    expected_banks,
                    expected_period,
                )
            )

        base.validate_matrix = (
            scoped_validate_matrix
        )

        validator_state["installed"] = True

        print("")
        print(
            "[Step06 Scope Contract Adapter]"
        )
        print(
            "  Runtime validator binding: INSTALLED"
        )
        print(
            "  Frozen Phase2 source modified: NO"
        )

    async def scoped_bootstrap_node(state):
        result = await original_bootstrap(state)

        install_validator_binding()

        return result

    async def scoped_guard_node(state):
        query = state.get(
            "query",
            "",
        )

        banks, token = (
            _set_request_scope(query)
        )

        expected_period = _resolve_target_period(query)
        period_token = _EXPECTED_PERIOD.set(expected_period)

        try:
            print("")
            print(
                "[Step06 Scope Contract Adapter]"
            )
            print(
                "  Guard expected banks:",
                banks,
            )

            result = original_guard(state)

            if inspect.isawaitable(result):
                return await result

            return result

        finally:
            _EXPECTED_PERIOD.reset(period_token)
            _reset_request_scope(token)
    async def scoped_revalidation_node(state):
        query = state.get(
            "query",
            "",
        )

        banks, token = (
            _set_request_scope(query)
        )

        expected_period = _resolve_target_period(query)
        period_token = _EXPECTED_PERIOD.set(expected_period)

        try:
            print("")
            print(
                "[Step06 Scope Contract Adapter]"
            )
            print(
                "  Revalidation expected banks:",
                banks,
            )

            result = original_revalidation(
                state
            )

            if inspect.isawaitable(result):
                return await result

            return result

        finally:
            _EXPECTED_PERIOD.reset(period_token)
            _reset_request_scope(token)
    runtime_module.runtime_bootstrap_node = (
        scoped_bootstrap_node
    )

    runtime_module.deterministic_guard_node = (
        scoped_guard_node
    )

    if original_revalidation is not None:
        runtime_module.deterministic_revalidation_node = (
            scoped_revalidation_node
        )

    runtime_module._step06_scope_contract_installed = (
        True
    )

    runtime_module._step06_scope_contract_state = (
        validator_state
    )

    return runtime_module
