from jobscraper.ats.detect import detect_ats


def test_detects_greenhouse_from_embedded_link():
    html = '<a href="https://boards.greenhouse.io/acme/jobs/1">AI Engineer</a>'
    result = detect_ats(html, "https://acme.com/careers")
    assert result is not None
    assert result.provider == "greenhouse"
    assert result.identifier == "acme"


def test_detects_lever_from_final_redirect_url():
    result = detect_ats("<html></html>", "https://jobs.lever.co/acme")
    assert result is not None
    assert result.provider == "lever"
    assert result.identifier == "acme"


def test_detects_workday_tenant_and_site():
    html = '<a href="https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite">Jobs</a>'
    result = detect_ats(html, "https://nvidia.com/careers")
    assert result is not None
    assert result.provider == "workday"
    assert result.identifier == "nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"


def test_no_match_returns_none():
    result = detect_ats("<html><body>plain careers page</body></html>", "https://acme.com/careers")
    assert result is None
