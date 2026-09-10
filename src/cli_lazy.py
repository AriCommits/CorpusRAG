"""Lazy-loading Click group for fast CLI startup."""

import importlib

import click


class LazyGroup(click.Group):
    """A Click group that lazily loads subcommands on first access.

    ``lazy_subcommands`` maps a command name to either:

    - a plain ``str`` import path (``"module.path:attr"``) with empty short
      help, or
    - a ``tuple[str, str]`` of ``(import_path, short_help)``.

    The short help is stored so that ``--help`` can render the command list
    without importing any subcommand modules.
    """

    def __init__(
        self,
        *args,
        lazy_subcommands: dict[str, str | tuple[str, str]] | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._lazy_subcommands: dict[str, str | tuple[str, str]] = lazy_subcommands or {}

    def _spec(self, name: str) -> tuple[str, str]:
        """Normalize a lazy entry into ``(import_path, short_help)``."""
        value = self._lazy_subcommands[name]
        if isinstance(value, tuple):
            import_path, short_help = value
            return import_path, short_help
        return value, ""

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.BaseCommand | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_lazy(cmd_name)
        return super().get_command(ctx, cmd_name)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Render the ``Commands`` section without importing lazy subcommands.

        Lazy commands use their stored short help. Eagerly registered commands
        are resolved via ``super().get_command`` so their ``short_help`` can be
        read the way Click does normally.
        """
        rows: list[tuple[str, str]] = []
        for name in self.list_commands(ctx):
            if name in self._lazy_subcommands:
                _, short_help = self._spec(name)
                rows.append((name, short_help))
            else:
                cmd = super().get_command(ctx, name)
                if cmd is None:
                    continue
                if cmd.hidden:
                    continue
                rows.append((name, cmd.get_short_help_str()))

        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)

    def _load_lazy(self, cmd_name: str) -> click.BaseCommand:
        import_path, _ = self._spec(cmd_name)
        module_path, attr_name = import_path.rsplit(":", 1)
        try:
            module = importlib.import_module(module_path)
            return getattr(module, attr_name)
        except ImportError:

            @click.group(name=cmd_name)
            def stub_group(**kwargs):
                pass

            @stub_group.command(name="generate")
            def stub_cmd():
                click.echo(f"{cmd_name.title()} requires the 'generators' extra.")
                click.echo("Install with: pip install corpusrag[generators]")
                raise SystemExit(1)

            return stub_group
