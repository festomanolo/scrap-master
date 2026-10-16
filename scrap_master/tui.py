# -*- coding: utf-8 -*-
"""MANOLO Scrap — terminal UI. Run with: scrap"""

import shutil
import subprocess
import sys
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    ContentSwitcher,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    RichLog,
    Select,
    Static,
    TextArea,
)

from scrap_master import __version__
from scrap_master.workspace import workspace_root

BANNER = r"""[b #ff8c42]
 __  __    _    _   _  ___  _     ___
|  \/  |  / \  | \ | |/ _ \| |   / _ \
| |\/| | / _ \ |  \| | | | | |  | | | |
| |  | |/ ___ \| |\  | |_| | |__| |_| |
|_|  |_/_/   \_\_| \_|\___/|_____\___/[/]  [dim]S C R A P[/]
"""

MENU = [
    ("ask", "🧠  Ask AI to scrape"),
    ("tools", "🛠   Tools"),
    ("viewer", "📄  File viewer"),
    ("settings", "⚙   Settings"),
    ("doctor", "🩺  Health check"),
]

TOOLS = [
    ("harvest", "Harvest site — crawl a page, grab every PDF/Drive/Scribd doc"),
    ("download", "Download URLs (space separated) — parallel + chunked"),
    ("scribd", "Scribd document → Markdown"),
    ("readpdf", "Read PDF (path) → Markdown with OCR"),
    ("read", "Read any web page → Markdown"),
    ("search", "Web search (no key needed)"),
]

TEXT_EXTS = {".md", ".txt", ".json", ".csv", ".py", ".log", ".html", ".yaml", ".yml"}

CSS = """
Screen { background: $surface; }
#sidebar { width: 34; border-right: tall $primary-darken-2; }
#menu { height: auto; max-height: 12; }
#menu > ListItem { padding: 0 1; }
#tree-title { padding: 1 1 0 1; color: $text-muted; }
#tree { height: 1fr; }
#main { padding: 0 1; }
#banner { height: auto; content-align: center middle; padding: 1 0 0 0; }
.hint { color: $text-muted; padding: 0 0 1 0; }
.row { height: auto; margin: 0 0 1 0; }
.row > Input { width: 1fr; }
.row > Select { width: 1fr; }
.row > Button { margin-left: 1; }
RichLog { border: round $primary-darken-1; height: 1fr; }
#viewer-md { height: 1fr; }
#viewer-text { height: 1fr; }
#viewer-path { color: $accent; padding: 0 0 1 0; }
.field-label { padding: 1 0 0 0; color: $text-muted; }
#settings Input, #settings Select { margin: 0 0 0 0; }
ModalScreen { align: center middle; }
#dialog { width: 64; height: auto; border: thick $primary; background: $panel; padding: 1 2; }
#dialog Horizontal { height: auto; align-horizontal: right; margin-top: 1; }
#dialog Button { margin-left: 1; }
"""


class Prompt(ModalScreen):
    """Ask for a line of text (or just confirm when ``value`` is None)."""

    BINDINGS = [Binding("escape", "dismiss(None)", "Cancel")]

    def __init__(self, title: str, value: str = "", confirm: bool = False):
        super().__init__()
        self._title, self._value, self._confirm = title, value, confirm

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self._title)
            if not self._confirm:
                yield Input(value=self._value, id="prompt-input")
            with Horizontal():
                yield Button("Cancel", id="cancel")
                yield Button("Delete" if self._confirm else "OK", variant="error" if self._confirm else "primary", id="ok")

    @on(Input.Submitted)
    def _submit(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    @on(Button.Pressed)
    def _press(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss(True if self._confirm else (self.query_one(Input).value.strip() or None))
        else:
            self.dismiss(None)


class ManoloScrap(App):
    TITLE = "MANOLO Scrap"
    SUB_TITLE = f"v{__version__}"
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+a", "show('ask')", "Ask AI"),
        Binding("ctrl+t", "show('tools')", "Tools"),
        Binding("ctrl+s", "show('settings')", "Settings"),
        Binding("n", "new_folder", "New folder"),
        Binding("f", "new_file", "New file"),
        Binding("r", "rename", "Rename"),
        Binding("delete", "delete", "Delete"),
        Binding("o", "reveal", "Open in Finder"),
        Binding("ctrl+e", "edit", "Edit/Save"),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(self):
        super().__init__()
        self.root = workspace_root()
        self.selected: Path = self.root
        self.editing: Path | None = None

    # ── layout ──────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield ListView(*[ListItem(Label(t), id=f"m-{k}") for k, t in MENU], id="menu")
                yield Label(f"📂 {self.root}", id="tree-title")
                yield DirectoryTree(self.root, id="tree")
            with ContentSwitcher(initial="ask", id="main"):
                with Vertical(id="ask"):
                    yield Static(BANNER, id="banner")
                    yield Label("Tell me what to scrape. I'll plan it, search, download, extract and file everything.",
                                classes="hint")
                    with Horizontal(classes="row"):
                        yield Input(placeholder="Today I want to scrape data about…", id="ask-input")
                        yield Button("Go", variant="success", id="ask-go")
                    yield RichLog(id="ask-log", markup=True, wrap=True)
                with Vertical(id="tools"):
                    yield Label("Pick a tool, paste a URL / path / query, press Enter.", classes="hint")
                    with Horizontal(classes="row"):
                        yield Select([(t, k) for k, t in TOOLS], value="harvest", allow_blank=False, id="tool-select")
                    with Horizontal(classes="row"):
                        yield Input(placeholder="https://…", id="tool-input")
                        yield Button("Run", variant="primary", id="tool-go")
                    yield RichLog(id="tool-log", markup=True, wrap=True)
                with Vertical(id="viewer"):
                    yield Label("Select a file in the tree.", id="viewer-path")
                    with ContentSwitcher(initial="viewer-md", id="viewer-switch"):
                        with VerticalScroll(id="viewer-md"):
                            yield Markdown("", id="md")
                        yield TextArea("", id="viewer-text", read_only=True)
                with VerticalScroll(id="settings"):
                    yield from self._settings_form()
                with Vertical(id="doctor"):
                    yield RichLog(id="doctor-log", markup=True, wrap=True)
        yield Footer()

    def _settings_form(self) -> ComposeResult:
        from scrap_master import ai
        from scrap_master.config import Config

        c = Config()
        info = ai.provider_info()
        models = ai.ollama_models()
        yield Label("AI provider", classes="field-label")
        yield Select([("Ollama (local, free)", "ollama"), ("OpenRouter (cloud)", "openrouter")],
                     value=info["provider"], allow_blank=False, id="s-provider")
        yield Label("Ollama model" + (f"  — installed: {', '.join(models)}" if models else "  — Ollama not running"),
                    classes="field-label")
        yield Input(value=c.get("ollama_model") or ai.DEFAULT_OLLAMA_MODEL, id="s-ollama-model")
        yield Label("OpenRouter API key", classes="field-label")
        yield Input(value=c.get("openrouter_api_key") or "", password=True, placeholder="sk-or-…", id="s-or-key")
        yield Label("OpenRouter model  — 'free' auto-picks a no-cost model; or e.g. google/gemma-4-31b-it:free",
                    classes="field-label")
        yield Input(value=c.get("openrouter_model") or ai.DEFAULT_OPENROUTER_MODEL, id="s-or-model")
        from scrap_master.agent import seed_sites

        yield Label("Favourite sites (comma separated — crawled when web search is down)", classes="field-label")
        yield Input(value=", ".join(seed_sites()), id="s-seeds")
        yield Label("Workspace folder (results go here)", classes="field-label")
        yield Input(value=str(self.root), id="s-workspace")
        with Horizontal(classes="row"):
            yield Button("Save", variant="success", id="s-save")
            yield Button("Test AI", id="s-test")
        yield Label("", id="s-status")

    def on_mount(self) -> None:
        self.query_one("#ask-input", Input).focus()
        log = self.query_one("#ask-log", RichLog)
        log.write(f"[dim]Results are filed under[/] [b]{self.root}/projects/<date>_<topic>/[/]")
        log.write("[dim]  pdfs/  markdown/  scribd/  pages/  data/  report.md[/]")

    # ── navigation ──────────────────────────────────────────
    def action_show(self, view: str) -> None:
        self.query_one("#main", ContentSwitcher).current = view
        if view == "doctor":
            self.run_doctor()
        focus = {"ask": "#ask-input", "tools": "#tool-input"}.get(view)
        if focus:
            self.query_one(focus).focus()

    @on(ListView.Selected, "#menu")
    def _menu(self, event: ListView.Selected) -> None:
        self.action_show(event.item.id.removeprefix("m-"))

    @on(DirectoryTree.FileSelected)
    def _file(self, event: DirectoryTree.FileSelected) -> None:
        self.selected = Path(event.path)
        self.open_file(self.selected)

    @on(DirectoryTree.DirectorySelected)
    def _dir(self, event: DirectoryTree.DirectorySelected) -> None:
        self.selected = Path(event.path)

    def open_file(self, path: Path) -> None:
        self.editing = None
        self.query_one("#viewer-path", Label).update(f"📄 {path}  [dim]({path.stat().st_size // 1024} KB)[/]")
        switch = self.query_one("#viewer-switch", ContentSwitcher)
        text_area = self.query_one("#viewer-text", TextArea)
        text_area.read_only = True
        if path.suffix.lower() == ".md":
            self.query_one("#md", Markdown).update(path.read_text(encoding="utf-8", errors="replace")[:400_000])
            switch.current = "viewer-md"
        elif path.suffix.lower() in TEXT_EXTS:
            text_area.load_text(path.read_text(encoding="utf-8", errors="replace")[:400_000])
            switch.current = "viewer-text"
        else:
            hint = "Press [b]o[/] to open it in the default app."
            if path.suffix.lower() == ".pdf":
                hint += "  Use Tools → Read PDF to extract text."
            self.query_one("#md", Markdown).update(f"**{path.name}** is a binary file.\n\n{hint}")
            switch.current = "viewer-md"
        self.action_show("viewer")

    # ── file operations ─────────────────────────────────────
    def _target_dir(self) -> Path:
        return self.selected if self.selected.is_dir() else self.selected.parent

    def action_refresh(self) -> None:
        self.query_one("#tree", DirectoryTree).reload()

    def _typing(self) -> bool:
        return isinstance(self.focused, (Input, TextArea)) and not getattr(self.focused, "read_only", False)

    def action_new_folder(self) -> None:
        if self._typing():
            return

        def done(name):
            if name:
                (self._target_dir() / name).mkdir(parents=True, exist_ok=True)
                self.action_refresh()
        self.push_screen(Prompt(f"New folder in {self._target_dir()}"), done)

    def action_new_file(self) -> None:
        if self._typing():
            return

        def done(name):
            if name:
                p = self._target_dir() / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch()
                self.action_refresh()
                self.selected = p
                self.open_file(p)
                self.action_edit()
        self.push_screen(Prompt(f"New file in {self._target_dir()}", "notes.md"), done)

    def action_rename(self) -> None:
        if self._typing() or self.selected == self.root:
            return

        def done(name):
            if name:
                new = self.selected.with_name(name)
                self.selected.rename(new)
                self.selected = new
                self.action_refresh()
        self.push_screen(Prompt(f"Rename {self.selected.name}", self.selected.name), done)

    def action_delete(self) -> None:
        if self._typing() or self.selected == self.root:
            return
        target = self.selected

        def done(ok):
            if ok:
                shutil.rmtree(target) if target.is_dir() else target.unlink()
                self.selected = target.parent
                self.action_refresh()
                self.notify(f"Deleted {target.name}")
        self.push_screen(Prompt(f"Delete {target}?", confirm=True), done)

    def action_reveal(self) -> None:
        if self._typing():
            return
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.Popen([opener, str(self.selected)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def action_edit(self) -> None:
        """Toggle edit mode for text files; pressing again saves."""
        if self.editing is None and self._typing():
            return
        p = self.selected
        if not p.is_file() or (p.suffix.lower() not in TEXT_EXTS and p.stat().st_size > 0):
            return
        ta = self.query_one("#viewer-text", TextArea)
        if self.editing == p:
            p.write_text(ta.text, encoding="utf-8")
            self.notify(f"Saved {p.name}")
            self.open_file(p)
            return
        ta.load_text(p.read_text(encoding="utf-8", errors="replace"))
        ta.read_only = False
        self.query_one("#viewer-switch", ContentSwitcher).current = "viewer-text"
        self.query_one("#viewer-path", Label).update(f"✏  {p}  [dim](editing — ctrl+e to save)[/]")
        self.editing = p
        self.action_show("viewer")
        ta.focus()

    # ── AI job ──────────────────────────────────────────────
    @on(Input.Submitted, "#ask-input")
    @on(Button.Pressed, "#ask-go")
    def _ask(self) -> None:
        inp = self.query_one("#ask-input", Input)
        if inp.value.strip():
            self.run_ai_job(inp.value.strip())
            inp.value = ""

    @work(thread=True, exclusive=True, group="ask")
    def run_ai_job(self, request: str) -> None:
        from scrap_master.agent import run_job

        log = self.query_one("#ask-log", RichLog)
        say = lambda m: self.call_from_thread(log.write, m)  # noqa: E731
        say(f"\n[b #ff8c42]▶ {request}[/]")
        try:
            project = run_job(request, log=say)
            self.call_from_thread(self.action_refresh)
            report = project / "report.md"
            self.call_from_thread(self._open_after, report)
        except Exception as e:
            say(f"[red]✖ {type(e).__name__}: {e}[/]")

    def _open_after(self, path: Path) -> None:
        self.selected = path
        self.notify("Job finished — opening report", timeout=4)
        self.open_file(path)

    # ── tools ───────────────────────────────────────────────
    @on(Select.Changed, "#tool-select")
    def _tool_changed(self, event: Select.Changed) -> None:
        ph = {"readpdf": "/path/to/file.pdf", "search": "search words…",
              "download": "https://a.pdf https://b.pdf"}.get(str(event.value), "https://…")
        self.query_one("#tool-input", Input).placeholder = ph

    @on(Input.Submitted, "#tool-input")
    @on(Button.Pressed, "#tool-go")
    def _tool(self) -> None:
        arg = self.query_one("#tool-input", Input).value.strip()
        if arg:
            self.run_tool(str(self.query_one("#tool-select", Select).value), arg)

    @work(thread=True, group="tools")
    def run_tool(self, tool: str, arg: str) -> None:
        from scrap_master.workspace import new_project, slugify

        log = self.query_one("#tool-log", RichLog)
        say = lambda m: self.call_from_thread(log.write, m)  # noqa: E731
        say(f"\n[b]▶ {tool}[/] {arg}")
        try:
            if tool == "harvest":
                from scrap_master.utils.harvest import discover, fetch

                project = new_project(arg.split("//")[-1])
                say("crawling…")
                rep = discover([arg], depth=1, max_pages=25)
                say(f"found {len(rep.items)} documents, downloading…")
                fetch(rep, project / "pdfs", extract_text=True, scribd_dir=project / "scribd",
                      text_dir=project / "markdown", manifest_dir=project / "data")
                for it in rep.items:
                    say(f"  {'✅' if it.ok else '❌'} [{it.kind}] {it.url}")
                say(f"[green]✔ {rep.ok_count}/{len(rep.items)} → {project}[/]")
            elif tool == "download":
                from scrap_master.channels.gdrive import extract_gdrive_id, get_direct_gdrive_url
                from scrap_master.utils.harvest import _safe_name
                from scrap_master.utils.parallel_downloader import download_batch_parallel

                inbox = self.root / "inbox"
                pairs = []
                for i, u in enumerate(arg.split(), 1):
                    gd = extract_gdrive_id(u)
                    name = f"gdrive_{gd[0]}.pdf" if gd else _safe_name(u, i)
                    pairs.append((get_direct_gdrive_url(u) if gd else u, inbox / name))
                for r in download_batch_parallel(pairs):
                    say(f"  {'✅' if r.ok else '❌ ' + r.error} {r.path.name} ({r.size_bytes // 1024} KB, {r.elapsed_sec}s)")
            elif tool == "scribd":
                from scrap_master.channels.scribd import ScribdChannel

                doc = ScribdChannel().extract_document(arg)
                out = self.root / "inbox" / f"scribd_{slugify(doc['title'])}.md"
                out.write_text(doc["markdown"], encoding="utf-8")
                say(f"[green]✔ {doc['title']} ({doc['page_count']} pages) → {out}[/]")
            elif tool == "readpdf":
                from scrap_master.utils.pdf_reader import extract_pdf_text

                src = Path(arg).expanduser()
                res = extract_pdf_text(str(src))
                out = src.with_suffix(".md")
                out.write_text(res["markdown"], encoding="utf-8")
                say(f"[green]✔ {res['total_pages']} pages (ocr={res['ocr_pages']}) → {out}[/]")
            elif tool == "read":
                from scrap_master.channels.web import WebChannel

                md = WebChannel().read(arg)
                out = self.root / "inbox" / f"{slugify(arg.split('//')[-1])}.md"
                out.write_text(md, encoding="utf-8")
                say(f"[green]✔ {len(md)} chars → {out}[/]")
            elif tool == "search":
                from scrap_master.agent import web_search

                for u in web_search(arg, 15):
                    say(f"  {u}")
            self.call_from_thread(self.action_refresh)
        except Exception as e:
            say(f"[red]✖ {type(e).__name__}: {e}[/]")

    # ── settings ────────────────────────────────────────────
    @on(Button.Pressed, "#s-save")
    def _save(self) -> None:
        from scrap_master.config import Config

        c = Config()
        c.set("ai_provider", str(self.query_one("#s-provider", Select).value))
        c.set("ollama_model", self.query_one("#s-ollama-model", Input).value.strip())
        c.set("openrouter_model", self.query_one("#s-or-model", Input).value.strip())
        c.set("seed_sites", self.query_one("#s-seeds", Input).value.strip())
        key = self.query_one("#s-or-key", Input).value.strip()
        if key:
            c.set("openrouter_api_key", key)
        ws = self.query_one("#s-workspace", Input).value.strip()
        if ws and Path(ws).expanduser() != self.root:
            c.set("workspace", ws)
            self.root = workspace_root()
            self.query_one("#tree", DirectoryTree).path = self.root
            self.query_one("#tree-title", Label).update(f"📂 {self.root}")
        self.query_one("#s-status", Label).update("[green]✔ Saved[/]")

    @on(Button.Pressed, "#s-test")
    def _test(self) -> None:
        self._save()
        self.test_ai()

    @work(thread=True)
    def test_ai(self) -> None:
        from scrap_master import ai

        status = self.query_one("#s-status", Label)
        self.call_from_thread(status.update, "testing…")
        try:
            reply = ai.chat([{"role": "user", "content": "Reply with exactly: MANOLO ready"}], timeout=60)
            self.call_from_thread(status.update, f"[green]✔ {ai.provider_info()['model']}: {reply.strip()[:80]}[/]")
        except Exception as e:
            self.call_from_thread(status.update, f"[red]✖ {e}[/]")

    # ── doctor ──────────────────────────────────────────────
    @work(thread=True, exclusive=True, group="doctor")
    def run_doctor(self) -> None:
        from scrap_master.doctor import check_all

        log = self.query_one("#doctor-log", RichLog)
        self.call_from_thread(log.clear)
        self.call_from_thread(log.write, "checking channels…")
        from scrap_master.config import Config

        results = check_all(Config())
        self.call_from_thread(log.clear)
        icons = {"ok": "✅", "warn": "⚠ ", "off": "⬜", "error": "❌"}
        for name, r in results.items():
            self.call_from_thread(
                log.write, f"{icons.get(r.get('status'), '•')} [b]{name:<12}[/] {r.get('message', '')}"
            )


def main() -> None:
    ManoloScrap().run()


if __name__ == "__main__":
    main()
