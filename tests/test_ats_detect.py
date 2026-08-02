from jobscraper.ats.detect import detect_ats


def test_detects_greenhouse_from_embedded_link():
    html = '<a href="https://boards.greenhouse.io/acme/jobs/1">AI Engineer</a>'
    result = detect_ats(html, "https://acme.com/careers")
    assert result is not None
    assert result.provider == "greenhouse"
    assert result.identifier == "acme"


def test_detects_greenhouse_embed_widget_via_for_query_param():
    html = '<script src="https://boards.greenhouse.io/embed/job_board/js?for=observeai"></script>'
    result = detect_ats(html, "https://www.observe.ai/careers")
    assert result is not None
    assert result.provider == "greenhouse"
    assert result.identifier == "observeai"


def test_detects_lever_from_final_redirect_url():
    result = detect_ats("<html></html>", "https://jobs.lever.co/acme")
    assert result is not None
    assert result.provider == "lever"
    assert result.identifier == "acme"


def test_detects_workday_tenant_and_site_with_locale_prefix():
    html = '<a href="https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite">Jobs</a>'
    result = detect_ats(html, "https://nvidia.com/careers")
    assert result is not None
    assert result.provider == "workday"
    assert result.identifier == "nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"


def test_detects_workday_site_without_locale_prefix_ignores_subpage():
    """Real bug: accenture.wd103.myworkdayjobs.com/AccentureCareers/userHome
    has no locale prefix — "AccentureCareers" is the site, "userHome" a
    subpage. The old regex misread this as "<locale>/<site>" and captured
    "userHome" as the site, which then 404'd against the real API."""
    html = '"https://accenture.wd103.myworkdayjobs.com/AccentureCareers/userHome"'
    result = detect_ats(html, "https://www.accenture.com/in-en/careers")
    assert result is not None
    assert result.provider == "workday"
    assert result.identifier == "accenture.wd103.myworkdayjobs.com/AccentureCareers"


def test_detects_ashby_identifier_with_url_encoded_space():
    """Real bug: jobs.ashbyhq.com/Jasper%20AI truncated to "Jasper" because
    the char class didn't include "%", silently dropping "%20AI"."""
    html = '<a href="https://jobs.ashbyhq.com/Jasper%20AI">Careers</a>'
    result = detect_ats(html, "https://www.jasper.ai/careers")
    assert result is not None
    assert result.provider == "ashby"
    assert result.identifier == "Jasper%20AI"


def test_detects_greenhouse_from_job_alert_signin_link():
    """Real case: HubSpot renders Greenhouse job data through its own custom
    UI with no boards.greenhouse.io reference anywhere, but still leaves a
    "create job alert" link at my.greenhouse.io/users/sign_in?job_board=X."""
    html = '<a href="https://my.greenhouse.io/users/sign_in?job_board=hubspotjobs">Create alert</a>'
    result = detect_ats(html, "https://www.hubspot.com/careers/jobs")
    assert result is not None
    assert result.provider == "greenhouse"
    assert result.identifier == "hubspotjobs"


def test_detects_workable_from_apply_url():
    html = '<a href="https://apply.workable.com/acme/j/ABC123">AI Engineer</a>'
    result = detect_ats(html, "https://acme.com/careers")
    assert result is not None
    assert result.provider == "workable"
    assert result.identifier == "acme"


def test_detects_recruitee_subdomain():
    result = detect_ats("<html></html>", "https://acme.recruitee.com/o/ai-engineer")
    assert result is not None
    assert result.provider == "recruitee"
    assert result.identifier == "acme"


def test_recruitee_skips_analytics_subdomain_false_positive():
    html = '<script src="https://careers-analytics.recruitee.com/track.js"></script>'
    result = detect_ats(html, "https://acme.com/careers")
    assert result is None


def test_detects_oracle_recruiting_host_and_site_number():
    html = (
        '<base href="/en/sites/jobsearch" '
        'data-apibaseurl="https://eeho.fa.us2.oraclecloud.com:443" '
        'data-fahosturl="https://eeho.fa.us2.oraclecloud.com:443" '
        'data-vanitybaseurl="https://careers.oracle.com/" '
        'data-sitenumber="CX_45001">'
    )
    result = detect_ats(html, "https://careers.oracle.com/en/sites/jobsearch")
    assert result is not None
    assert result.provider == "oracle_recruiting"
    assert result.identifier == "eeho.fa.us2.oraclecloud.com|CX_45001"


def test_no_match_returns_none():
    result = detect_ats("<html><body>plain careers page</body></html>", "https://acme.com/careers")
    assert result is None
