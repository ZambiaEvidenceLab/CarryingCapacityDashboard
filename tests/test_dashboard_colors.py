from cca.dashboard.colors import SECTOR_HUE_ANCHOR, SECTOR_RAMP

SECTORS = ["Health", "Education", "Agriculture", "Infrastructure", "Environment"]


class TestSectorHueAnchor:
    def test_has_one_distinct_hue_per_sector(self):
        assert set(SECTOR_HUE_ANCHOR) == set(SECTORS)
        assert len(set(SECTOR_HUE_ANCHOR.values())) == len(SECTORS)


class TestSectorRamp:
    def test_has_one_ramp_per_sector(self):
        assert set(SECTOR_RAMP) == set(SECTORS)

    def test_each_ramp_has_a_light_middle_and_dark_stop(self):
        for ramp in SECTOR_RAMP.values():
            assert [stop for stop, _ in ramp] == [0.0, 0.5, 1.0]

    def test_each_ramp_reads_light_to_dark_darker_meaning_higher_capacity(self):
        # Rough lightness proxy: average of the RGB channels. The light stop
        # must read paler than the middle stop, which must read paler than
        # the dark stop (dark = high capacity, ADR-0017).
        def _brightness(hex_color: str) -> float:
            hex_color = hex_color.lstrip("#")
            return sum(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        for sector, ramp in SECTOR_RAMP.items():
            light, mid, dark = (_brightness(hex_color) for _, hex_color in ramp)
            assert light > mid > dark, f"{sector}'s ramp isn't monotonically light->dark"

    def test_each_ramps_middle_stop_is_that_sectors_hue_anchor(self):
        for sector, ramp in SECTOR_RAMP.items():
            assert ramp[1][1] == SECTOR_HUE_ANCHOR[sector]
