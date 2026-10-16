from scrap_master import bench


def test_bench_scores_scrap_highest_on_tiny_batch():
    res = bench.run(files=10, size_kb=64, kbps=4096, latency_ms=5, log=lambda m: None,
                    tools=["naive", "MANOLO"])
    by = {r.tool: r for r in res}
    scrap = by["MANOLO Scrap"]
    assert scrap.ok_files == scrap.total_files == 3
    assert scrap.filtered and scrap.organized
    assert not by["python loop (naive)"].filtered
    assert res[0] is scrap
    assert "MANOLO Scrap" in bench.render(res)
