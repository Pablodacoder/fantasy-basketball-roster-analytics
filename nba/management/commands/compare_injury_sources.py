from django.core.management.base import BaseCommand

from nba.data import injuries
from nba.data.load import build_name_index


class Command(BaseCommand):
    help = "Compare the injury sources without saving anything."

    def handle(self, *args, **options):
        names = build_name_index()
        if not names:
            self.stdout.write("No active players yet. Run refresh_data --skip-injuries first.")
            return

        for source in injuries.SOURCES:
            try:
                rows = injuries.fetch_injuries(source)
            except Exception as exc:
                self.stdout.write(f"\n{source}: FAILED -> {exc}")
                continue

            teams = {r["team"] for r in rows}
            matched = sum(1 for r in rows if len(names.get(injuries.normalize_name(r["player_name"]), [])) == 1)
            unmapped = sorted({r["raw_status"] for r in rows if injuries.map_status(r["raw_status"]) is None})

            self.stdout.write(f"\n{source}:")
            self.stdout.write(f"  players listed:    {len(rows)}")
            self.stdout.write(f"  teams covered:     {len(teams)} / 30")
            self.stdout.write(f"  names matched:     {matched} / {len(rows)}")
            self.stdout.write(f"  unmapped statuses: {', '.join(unmapped) or 'none'}")