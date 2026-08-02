# Companies we can't reliably get jobs from right now

Generated from 215 companies in data/companies.csv
(DB status cross-referenced from data/jobscraper.db where available).

## ATS detected but no adapter built for it (0)
These were manually identified (e.g. from ATS_TODO.md research) but we
don't have a working integration — most need a browser/paid API, so they
stay generic-HTML-only unless a new adapter gets built.


## ATS/adapter currently failing to fetch (1)
We have a real adapter for these, but the last run errored — bot-blocked,
stale identifier, or the site is temporarily down. Worth checking first,
these are often a quick CSV URL or identifier fix (see README).

- [Tier 1] Intel — ats=workday/intel.wd1.myworkdayjobs.com/External — error: HTTP 403

## No ATS detected at all (155)
Falls back to generic HTML keyword parsing, which is lower-precision and
often finds 0 jobs (client-side-rendered pages, hard bot walls, or a
genuinely custom hiring platform). Run scripts/detect_ats_browser.py, or
check manually via ATS_TODO.md.

- [Tier 1] Affine Analytics — https://affine.ai/careers
- [Tier 1] Airbnb — https://careers.airbnb.com
- [Tier 1] Amazon — https://www.amazon.jobs
- [Tier 1] American Express India — https://www.americanexpress.com/en-us/careers/
- [Tier 1] Apple — https://jobs.apple.com
- [Tier 1] Atlassian — https://www.atlassian.com/company/careers
- [Tier 1] Atlassian India — https://www.atlassian.com/company/careers
- [Tier 1] BT Group — https://www.bt.com/careers
- [Tier 1] Capgemini India — https://www.capgemini.com/careers/
- [Tier 1] Capgemini UK — https://www.capgemini.com/gb-en/careers/
- [Tier 1] Cisco India — https://jobs.cisco.com
- [Tier 1] Coforge — https://www.coforge.com/careers
- [Tier 1] Cognizant — https://careers.cognizant.com
- [Tier 1] Deloitte India — https://www2.deloitte.com/in/en/careers.html
- [Tier 1] Deloitte UK — https://www2.deloitte.com/uk/en/careers.html
- [Tier 1] EY India — https://www.ey.com/en_in/careers
- [Tier 1] EY UK — https://www.ey.com/en_uk/careers
- [Tier 1] Goldman Sachs India — https://www.goldmansachs.com/careers/
- [Tier 1] Google — https://careers.google.com
- [Tier 1] Gramener — https://gramener.com/careers (error: HTTP 403)
- [Tier 1] HCLTech — https://www.hcltech.com/careers
- [Tier 1] HSBC Digital — https://www.hsbc.com/careers
- [Tier 1] Hexaware Technologies — https://hexaware.com/careers/ (error: HTTP 403)
- [Tier 1] IBM — https://www.ibm.com/careers
- [Tier 1] Indium Software — https://www.indiumsoftware.com/careers
- [Tier 1] Infosys — https://www.infosys.com/careers.html (error: HTTP 403)
- [Tier 1] JPMorgan Chase India — https://careers.jpmorgan.com
- [Tier 1] KPMG India — https://home.kpmg/in/en/home/careers.html
- [Tier 1] KPMG UK — https://www.kpmgcareers.co.uk
- [Tier 1] LTIMindtree — https://www.ltm.com/us-careers
- [Tier 1] LatentView Analytics — https://www.latentview.com/career/
- [Tier 1] LinkedIn India — https://careers.linkedin.com
- [Tier 1] Meta — https://www.metacareers.com (error: HTTP 400)
- [Tier 1] Micron India — https://www.micron.com/careers
- [Tier 1] Microsoft — https://careers.microsoft.com
- [Tier 1] Mphasis — https://careers.mphasis.com
- [Tier 1] Mu Sigma — https://www.mu-sigma.com/careers
- [Tier 1] NTT DATA India — https://in.nttdata.com/careers
- [Tier 1] NatWest Digital — https://jobs.natwestgroup.com (error: HTTP 403)
- [Tier 1] Netflix — https://jobs.netflix.com
- [Tier 1] Nutanix India — https://www.nutanix.com/company/careers
- [Tier 1] PayPal India — https://careers.pypl.com
- [Tier 1] Persistent Systems — https://www.persistent.com/careers/
- [Tier 1] Pinterest — https://www.pinterestcareers.com
- [Tier 1] PwC India — https://www.pwc.in/careers.html
- [Tier 1] PwC UK — https://www.pwc.co.uk/careers.html
- [Tier 1] Qualcomm — https://www.qualcomm.com/company/careers
- [Tier 1] Rubrik India — https://www.rubrik.com/company/careers (error: HTTP 403)
- [Tier 1] SAP Labs India — https://jobs.sap.com
- [Tier 1] Sage — https://www.sage.com/en-us/company/careers/career-search/
- [Tier 1] Salesforce — https://careers.salesforce.com (error: HTTP 403)
- [Tier 1] Salesforce India — https://careers.salesforce.com (error: HTTP 403)
- [Tier 1] ServiceNow — https://careers.servicenow.com
- [Tier 1] ServiceNow India — https://careers.servicenow.com
- [Tier 1] Sigmoid — https://www.sigmoid.com/careers
- [Tier 1] Snap Inc. — https://careers.snap.com
- [Tier 1] Sonata Software — https://www.sonata-software.com/careers
- [Tier 1] Spotify — https://www.lifeatspotify.com/jobs
- [Tier 1] TCS — https://www.tcs.com/careers (error: HTTP 403)
- [Tier 1] Target India — https://india.target.com/careers
- [Tier 1] Tech Mahindra — https://careers.techmahindra.com
- [Tier 1] Thoughtworks India — https://www.thoughtworks.com/careers
- [Tier 1] Thoughtworks UK — https://www.thoughtworks.com/careers
- [Tier 1] Tredence — https://www.tredence.com/company-careers
- [Tier 1] Twilio — https://www.twilio.com/en-us/company/jobs
- [Tier 1] Uber — https://www.uber.com/careers/
- [Tier 1] Visa India — https://usa.visa.com/careers.html (error: HTTP 403)
- [Tier 1] Vodafone — https://careers.vodafone.com
- [Tier 1] WNS Global Services — https://www.wns.com/careers
- [Tier 1] Walmart Global Tech India — https://careers.walmart.com/global-tech
- [Tier 1] Wipro — https://careers.wipro.com
- [Tier 2] Automattic (WordPress.com) — https://automattic.com/work-with-us/
- [Tier 2] Brex — https://www.brex.com/careers
- [Tier 2] CRED — https://careers.cred.club
- [Tier 2] Chargebee — https://www.chargebee.com/careers/
- [Tier 2] CleverTap — https://clevertap.com/careers/
- [Tier 2] Cloudflare — https://www.cloudflare.com/careers/
- [Tier 2] CoRover.ai — https://corover.ai/company/careers
- [Tier 2] Coinbase — https://www.coinbase.com/careers
- [Tier 2] Darwinbox — https://www.darwinbox.com/careers
- [Tier 2] Datadog — https://careers.datadoghq.com
- [Tier 2] Datamatics — https://www.datamatics.com/human-resources/job-openings
- [Tier 2] Deliveroo — https://careers.deliveroo.co.uk
- [Tier 2] Elastic — https://www.elastic.co/careers
- [Tier 2] Faculty AI — https://faculty.ai/careers/ (error: HTTP 404)
- [Tier 2] GitLab — https://about.gitlab.com/jobs/
- [Tier 2] Graphcore — https://www.graphcore.ai/careers
- [Tier 2] Groww — https://groww.in/careers
- [Tier 2] Haptik — https://haptik.ai/careers
- [Tier 2] HashiCorp — https://www.hashicorp.com/careers (error: 429 Client Error: Too Many Requests for url: https://www.hashicorp.com/careers)
- [Tier 2] Hasura — https://hasura.io/careers
- [Tier 2] Icertis — https://www.icertis.com/company/careers/
- [Tier 2] Improbable — https://www.improbable.io/careers
- [Tier 2] Innovaccer — https://innovaccer.com/careers
- [Tier 2] Instabase — https://instabase.com/careers/
- [Tier 2] Jocata — https://www.jocata.com/careers
- [Tier 2] Jupiter Money — https://jupiter.money/careers/
- [Tier 2] Kissflow — https://kissflow.com/careers/
- [Tier 2] LeadSquared — https://www.leadsquared.com/careers/
- [Tier 2] Locus.sh — https://locus.sh/careers
- [Tier 2] MoEngage — https://www.moengage.com/careers/
- [Tier 2] MongoDB — https://www.mongodb.com/careers
- [Tier 2] Ocado Technology — https://www.ocadogroup.com/careers
- [Tier 2] Okta — https://www.okta.com/company/careers/
- [Tier 2] PhonePe — https://www.phonepe.com/careers/
- [Tier 2] PolyAI — https://poly.ai/careers/
- [Tier 2] Postman — https://www.postman.com/company/careers/
- [Tier 2] Remote.com — https://remote.com/careers
- [Tier 2] Revolut — https://www.revolut.com/careers/
- [Tier 2] Rippling — https://www.rippling.com/careers
- [Tier 2] Rocketlane — https://careers.kula.ai/rocketlane
- [Tier 2] Sahaj Software — https://sahaj.ai/careers
- [Tier 2] Setu — https://setu.co/careers
- [Tier 2] Signzy — https://signzy.com/careers/
- [Tier 2] Slice — https://sliceit.com/careers
- [Tier 2] Snowflake — https://careers.snowflake.com
- [Tier 2] Splunk (Cisco) — https://www.splunk.com/en_us/careers.html
- [Tier 2] Starling Bank — https://www.starlingbank.com/careers/
- [Tier 2] Stripe — https://stripe.com/jobs
- [Tier 2] Swiggy — https://careers.swiggy.com
- [Tier 2] Techolution — https://www.techolution.com/careers
- [Tier 2] Urban Company — https://careers.urbancompany.com
- [Tier 2] Verloop.io — https://verloop.io/careers/ (error: HTTP 403)
- [Tier 2] Vernacular.ai (Skit.ai) — https://www.skit.ai/careers
- [Tier 2] Vymo — https://vymo.com/careers/
- [Tier 2] Whatfix — https://whatfix.com/careers/
- [Tier 2] Wise — https://wise.jobs
- [Tier 2] Yellow.ai — https://yellow.ai/career/
- [Tier 2] Zapier — https://zapier.com/jobs
- [Tier 2] Zepto — https://www.zeptonow.com/careers
- [Tier 2] Zeta — https://www.zeta.tech/in/careers
- [Tier 2] Zoho — https://www.zoho.com/careers.html
- [Tier 2] Zomato / Eternal — https://www.zomato.com/careers
- [Tier 3] Abnormal Security — https://abnormalsecurity.com/careers
- [Tier 3] Anthropic — https://www.anthropic.com/careers
- [Tier 3] DataRobot — https://www.datarobot.com/careers/
- [Tier 3] Databricks — https://www.databricks.com/company/careers
- [Tier 3] Draup — https://draup.com/job-openings
- [Tier 3] ElevenLabs — https://elevenlabs.io/careers
- [Tier 3] Entropik — https://www.entropik.io/careers
- [Tier 3] Glean — https://www.glean.com/careers
- [Tier 3] Gong — https://www.gong.io/careers/
- [Tier 3] Google DeepMind — https://deepmind.google/careers/
- [Tier 3] Iris.ai — https://iris.ai/careers/
- [Tier 3] Krutrim (Ola) — https://www.olacareers.com (error: HTTPSConnectionPool(host='www.olacareers.com', port=443): Max retries exceeded with url: / (Caused by NameResolutionError("HTTPSConnection(host='www.olacareers.com', port=443): Failed to resolve 'www.olacareers.com' ([Errno -2] Name or service not known)")))
- [Tier 3] Modal — https://modal.com/careers
- [Tier 3] Onfido — https://onfido.com/careers/ (error: HTTP 403)
- [Tier 3] OpenAI — https://openai.com/careers/
- [Tier 3] Perplexity AI — https://www.perplexity.ai/careers
- [Tier 3] Quantexa — https://www.quantexa.com/careers/
- [Tier 3] Replicate — https://replicate.com/about
- [Tier 3] Synthesia — https://www.synthesia.io/careers
- [Tier 3] Toptal — https://www.toptal.com/talent/apply
- [Tier 3] Turing — https://www.turing.com/jobs
- [Tier 3] Wysa — https://www.wysa.io/careers
