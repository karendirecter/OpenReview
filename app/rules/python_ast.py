import ast

from app.review.models import IssueHit


class PythonAstAnalyzer:
    def __init__(self, commit_sha: str) -> None:
        self.commit_sha = commit_sha

    def analyze(self, file_path: str, diff: str) -> list[IssueHit]:
        tree = ast.parse(diff)
        hits: list[IssueHit] = []
        parent_map = build_parent_map(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                hits.extend(self._find_blocking_calls(file_path, node))
                hits.extend(self._find_blocking_http_calls(file_path, node))
                hits.extend(self._find_missing_await(file_path, node, parent_map))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                hits.extend(self._find_none_dereference(file_path, node))
                hits.extend(self._find_resource_leak(file_path, node))
        return hits

    def _find_blocking_calls(self, file_path: str, node: ast.AsyncFunctionDef) -> list[IssueHit]:
        hits: list[IssueHit] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            evidence = blocking_call_evidence(child)
            if not evidence:
                continue
            hits.append(
                IssueHit(
                    file_path=file_path,
                    line_number=child.lineno,
                    end_line_number=child.lineno,
                    commit_sha=self.commit_sha,
                    rule_id="python.async-blocking-io",
                    severity="high",
                    message="Blocking call used inside async function.",
                    evidence=evidence,
                )
            )
        return dedupe_hits(hits)

    def _find_none_dereference(self, file_path: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[IssueHit]:
        maybe_none_names = collect_maybe_none_names(node)
        hits: list[IssueHit] = []

        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                if child.value.id in maybe_none_names:
                    hits.append(
                        IssueHit(
                            file_path=file_path,
                            line_number=child.lineno,
                            end_line_number=child.lineno,
                            commit_sha=self.commit_sha,
                            rule_id="python.none-dereference",
                            severity="high",
                            message="Possible None dereference from optional value.",
                            evidence=f"{child.value.id}.{child.attr}",
                        )
                    )
            if isinstance(child, ast.Subscript) and isinstance(child.value, ast.Name):
                if child.value.id in maybe_none_names:
                    hits.append(
                        IssueHit(
                            file_path=file_path,
                            line_number=child.lineno,
                            end_line_number=child.lineno,
                            commit_sha=self.commit_sha,
                            rule_id="python.none-dereference",
                            severity="high",
                            message="Possible None dereference from optional value.",
                            evidence=f"{child.value.id}[...]",
                        )
                    )
        return dedupe_hits(hits)

    def _find_resource_leak(self, file_path: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[IssueHit]:
        open_handles: dict[str, int] = {}
        closed_handles: set[str] = set()
        with_handles: set[str] = set()

        for child in ast.walk(node):
            if isinstance(child, ast.With):
                for item in child.items:
                    if isinstance(item.context_expr, ast.Call) and isinstance(item.context_expr.func, ast.Name):
                        if item.context_expr.func.id == "open" and isinstance(item.optional_vars, ast.Name):
                            with_handles.add(item.optional_vars.id)
            if isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
                if isinstance(child.value, ast.Call) and isinstance(child.value.func, ast.Name) and child.value.func.id == "open":
                    open_handles[child.targets[0].id] = child.lineno
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if child.func.attr == "close" and isinstance(child.func.value, ast.Name):
                    closed_handles.add(child.func.value.id)

        hits: list[IssueHit] = []
        for handle_name, lineno in open_handles.items():
            if handle_name in closed_handles or handle_name in with_handles:
                continue
            hits.append(
                IssueHit(
                    file_path=file_path,
                    line_number=lineno,
                    end_line_number=lineno,
                    commit_sha=self.commit_sha,
                    rule_id="python.resource-leak",
                    severity="medium",
                    message="File handle opened without an obvious close().",
                    evidence=f"{handle_name} = open(...)",
                )
            )
        return dedupe_hits(hits)

    def _find_missing_await(
        self,
        file_path: str,
        node: ast.AsyncFunctionDef,
        parent_map: dict[ast.AST, ast.AST],
    ) -> list[IssueHit]:
        hits: list[IssueHit] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue
            parent = parent_map.get(child)
            if isinstance(parent, ast.Await):
                continue
            if not isinstance(parent, (ast.Return, ast.Expr, ast.Assign)):
                continue
            if not looks_async_call(child):
                continue

            hits.append(
                IssueHit(
                    file_path=file_path,
                    line_number=child.lineno,
                    end_line_number=child.lineno,
                    commit_sha=self.commit_sha,
                    rule_id="python.missing-await",
                    severity="high",
                    message="Possible missing await in async function.",
                    evidence=render_call_name(child),
                )
            )
        return dedupe_hits(hits)

    def _find_blocking_http_calls(self, file_path: str, node: ast.AsyncFunctionDef) -> list[IssueHit]:
        hits: list[IssueHit] = []
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
                continue
            if getattr(child.func.value, "id", None) == "requests" and child.func.attr in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
            }:
                hits.append(
                    IssueHit(
                        file_path=file_path,
                        line_number=child.lineno,
                        end_line_number=child.lineno,
                        commit_sha=self.commit_sha,
                        rule_id="python.async-blocking-http",
                        severity="high",
                        message="Synchronous requests call used inside async function.",
                        evidence=f"requests.{child.func.attr}(...)",
                    )
                )
        return dedupe_hits(hits)


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parent_map: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[child] = parent
    return parent_map


def render_call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return f"{call.func.id}(...)"
    if isinstance(call.func, ast.Attribute):
        return f"{call.func.attr}(...)"
    return "call(...)"


def looks_async_call(call: ast.Call) -> bool:
    async_markers = ("fetch", "load", "save", "create", "update", "delete", "post", "put", "query")
    if isinstance(call.func, ast.Name):
        return call.func.id.endswith("_async") or call.func.id.startswith(async_markers)
    if isinstance(call.func, ast.Attribute):
        if getattr(call.func.value, "id", None) == "asyncio" and call.func.attr == "sleep":
            return True
        return call.func.attr.endswith("_async") or call.func.attr.startswith(async_markers)
    return False


def collect_maybe_none_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    maybe_none_names = collect_none_default_args(node)

    for child in ast.walk(node):
        if isinstance(child, ast.Assign) and len(child.targets) == 1 and isinstance(child.targets[0], ast.Name):
            target = child.targets[0].id
            if isinstance(child.value, ast.Constant) and child.value.value is None:
                maybe_none_names.add(target)
            if (
                isinstance(child.value, ast.Call)
                and isinstance(child.value.func, ast.Attribute)
                and child.value.func.attr == "get"
            ):
                maybe_none_names.add(target)

    return maybe_none_names


def collect_none_default_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    maybe_none_names: set[str] = set()
    positional_args = list(node.args.args)
    if node.args.defaults:
        args_with_defaults = positional_args[-len(node.args.defaults) :]
        for arg, default in zip(args_with_defaults, node.args.defaults, strict=False):
            if isinstance(default, ast.Constant) and default.value is None:
                maybe_none_names.add(arg.arg)

    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=False):
        if isinstance(default, ast.Constant) and default.value is None:
            maybe_none_names.add(arg.arg)

    return maybe_none_names


def blocking_call_evidence(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        base_name = getattr(call.func.value, "id", None)
        if base_name == "time" and call.func.attr == "sleep":
            return "time.sleep(...)"
        if base_name == "subprocess" and call.func.attr in {"run", "call", "check_call", "check_output"}:
            return f"subprocess.{call.func.attr}(...)"
        if base_name == "os" and call.func.attr == "system":
            return "os.system(...)"
    return ""


def dedupe_hits(hits: list[IssueHit]) -> list[IssueHit]:
    seen: set[tuple[str, int, str]] = set()
    unique: list[IssueHit] = []
    for hit in hits:
        key = (hit.file_path, hit.line_number, hit.rule_id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique
