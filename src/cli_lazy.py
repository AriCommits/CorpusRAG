"""Lazy-loading Click group for fast CLI startup."""

import importlib

import click


class LazyGroup(click.Group):
    """A Click group that lazily loads subcommands on first access."""

    def __init__(self, *args, lazy_subcommands: dict[str, str] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._lazy_subcommands = lazy_subcommands or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        base = super().list_commands(ctx)
        lazy = sorted(self._lazy_subcommands.keys())
        return base + lazy

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.BaseCommand | None:
        if cmd_name in self._lazy_subcommands:
            return self._load_lazy(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _load_lazy(self, cmd_name: str) -> click.BaseCommand:
        import_path = self._lazy_subcommands[cmd_name]
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
