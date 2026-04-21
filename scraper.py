"""
LinkedIn scraper — profiles, jobs, companies via public pages.

Strategy:
  - Public profiles: accessible without login at /in/{slug}
  - Job search: accessible at /jobs/search/?keywords=...
  - Company pages: accessible at /company/{slug}
  - People search: requires login session (stored in .sessions/)

LinkedIn is aggressive with bot detection:
  - Rate limit: ~50 pages/hour before soft blocks
  - Hard blocks show CAPTCHA or "unusual activity" page
  - Session cookies from manual login bypass most checks
  - Random delays between requests are essential

Login flow:
  1. User logs in manually via `login` tool (opens headed browser)
  2. Session cookies saved to .sessions/linkedin.json
  3. All subsequent scraping uses these cookies in headless mode
"""

import asyncio
import json
import re
import logging
from urllib.parse import quote_plus, urlencode

from models import Profile, Job, Company, SearchResult
from stealth_browser import StealthBrowser

logger = logging.getLogger(__name__)

BASE_URL = "https://www.linkedin.com"


class LinkedInScraper:
    """Scrapes LinkedIn for profiles, jobs, and company data."""

    def __init__(self, browser: StealthBrowser | None = None):
        self._browser = browser or StealthBrowser()
        self._own_browser = browser is None

    async def login(self) -> bool:
        """Open a headed browser for manual LinkedIn login.

        The user logs in manually, then we save the session cookies
        for headless use in subsequent scraping.

        Returns True if login session was saved.
        """
        context = await self._browser.new_context(
            headed=True, session_name="linkedin"
        )
        page = await context.new_page()

        try:
            await page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")

            # Wait for user to log in — detect the feed page
            logger.info("Waiting for manual login... (complete login in the browser)")
            try:
                await page.wait_for_url(
                    "**/feed/**", timeout=120000  # 2 minutes to log in
                )
            except Exception:
                # Check if we're on any authenticated page
                current_url = page.url
                if "/login" in current_url or "/checkpoint" in current_url:
                    logger.warning("Login not completed within timeout")
                    return False

            # Save session
            await self._browser.save_session(context, "linkedin")
            logger.info("LinkedIn session saved successfully")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
        finally:
            await page.close()
            await context.close()

    async def _is_logged_in(self, page) -> bool:
        """Check if current page indicates a logged-in state."""
        try:
            # Logged-in pages have the global nav
            nav = page.locator("#global-nav, nav.global-nav").first
            await nav.wait_for(timeout=3000)
            return True
        except Exception:
            return False

    async def get_profile(
        self,
        profile_url: str = "",
        username: str = "",
        headed: bool = False,
    ) -> Profile | None:
        """Get a LinkedIn profile.

        Args:
            profile_url: Full LinkedIn profile URL
            username: LinkedIn username/slug (e.g. "johndoe")
            headed: Use visible browser
        """
        if not profile_url and not username:
            return None

        url = profile_url or f"{BASE_URL}/in/{username}/"

        context = await self._browser.new_context(
            headed=headed, session_name="linkedin"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Check for auth wall
            if await self._is_auth_wall(page):
                logger.warning("Auth wall detected — login required")
                # Try public view
                profile = await self._extract_public_profile(page)
                if profile and profile.name:
                    return profile
                return None

            profile = await self._extract_profile(page)
            await self._browser.save_session(context, "linkedin")
            return profile

        except Exception as e:
            logger.error(f"Profile fetch failed: {e}")
            return None
        finally:
            await page.close()
            await context.close()

    async def search_people(
        self,
        query: str,
        location: str = "",
        company: str = "",
        title: str = "",
        max_results: int = 20,
        headed: bool = False,
    ) -> SearchResult:
        """Search for people on LinkedIn.

        Requires login session for full results.

        Args:
            query: Search keywords
            location: Filter by location
            company: Filter by current company
            title: Filter by current title
            max_results: Maximum results (default 20)
            headed: Use visible browser
        """
        params = {"keywords": query, "origin": "GLOBAL_SEARCH_HEADER"}
        if location:
            params["geoUrn"] = location
        if company:
            params["company"] = company
        if title:
            params["title"] = title

        url = f"{BASE_URL}/search/results/people/?{urlencode(params)}"

        context = await self._browser.new_context(
            headed=headed, session_name="linkedin"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for search results to render
            try:
                await page.wait_for_selector(
                    'li.reusable-search__result-container, '
                    'div[data-view-name="search-entity-result-universal-template"], '
                    'div.search-results-container li, '
                    'ul.reusable-search__entity-result-list > li',
                    timeout=5000,
                )
            except Exception:
                pass
            await asyncio.sleep(1)
            await page.evaluate('window.scrollBy(0, 400)')
            await asyncio.sleep(0.5)

            if await self._is_auth_wall(page):
                return SearchResult(
                    query=query,
                    result_type="people",
                    results=[{"error": "Login required for people search"}],
                )

            result = await self._extract_people_search(page, query, max_results)
            await self._browser.save_session(context, "linkedin")
            return result

        except Exception as e:
            logger.error(f"People search failed: {e}")
            return SearchResult(query=query, result_type="people")
        finally:
            await page.close()
            await context.close()

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        remote: str = "",
        job_type: str = "",
        experience: str = "",
        max_results: int = 25,
        headed: bool = False,
    ) -> SearchResult:
        """Search for jobs on LinkedIn (works without login).

        Args:
            query: Job title or keywords
            location: Location filter
            remote: "remote", "onsite", "hybrid"
            job_type: "full-time", "part-time", "contract", "internship"
            experience: "internship", "entry", "associate", "mid-senior", "director", "executive"
            max_results: Maximum results (default 25)
            headed: Use visible browser
        """
        params = {"keywords": quote_plus(query), "position": 1, "pageNum": 0}
        if location:
            params["location"] = location

        # Remote filter
        remote_map = {"remote": "2", "onsite": "1", "hybrid": "3"}
        if remote and remote.lower() in remote_map:
            params["f_WT"] = remote_map[remote.lower()]

        # Job type filter
        type_map = {
            "full-time": "F", "part-time": "P",
            "contract": "C", "internship": "I", "temporary": "T",
        }
        if job_type and job_type.lower() in type_map:
            params["f_JT"] = type_map[job_type.lower()]

        # Experience level
        exp_map = {
            "internship": "1", "entry": "2", "associate": "3",
            "mid-senior": "4", "director": "5", "executive": "6",
        }
        if experience and experience.lower() in exp_map:
            params["f_E"] = exp_map[experience.lower()]

        url = f"{BASE_URL}/jobs/search/?{urlencode(params)}"

        context = await self._browser.new_context(
            headed=headed, session_name="linkedin"
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # Wait for job cards to render (LinkedIn loads them dynamically)
            try:
                await page.wait_for_selector(
                    'div.job-search-card, li.jobs-search-results__list-item, '
                    'div[data-job-id], li[data-occludable-job-id], '
                    'ul.jobs-search__results-list > li, '
                    'div.scaffold-layout__list-container li',
                    timeout=5000,
                )
            except Exception:
                pass
            await asyncio.sleep(1)
            # Scroll to trigger lazy-loaded items
            await page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(0.5)

            result = await self._extract_job_search(page, query, max_results)
            await self._browser.save_session(context, "linkedin")
            return result

        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return SearchResult(query=query, result_type="jobs")
        finally:
            await page.close()
            await context.close()

    async def get_company(
        self,
        company_url: str = "",
        company_slug: str = "",
        headed: bool = False,
    ) -> Company | None:
        """Get company page data.

        Args:
            company_url: Full LinkedIn company URL
            company_slug: Company slug (e.g. "google")
            headed: Use visible browser
        """
        import traceback
        
        if not company_url and not company_slug:
            logger.warning("get_company called without company_url or company_slug")
            return None

        url = company_url or f"{BASE_URL}/company/{company_slug}/"
        logger.info(f"get_company: fetching {url}")

        try:
            logger.info("Creating browser context...")
            context = await self._browser.new_context(
                headed=headed, session_name="linkedin"
            )
            logger.info("Creating page...")
            page = await context.new_page()

            try:
                logger.info(f"Navigating to {url}...")
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                logger.info("Page loaded, waiting for content...")
                await asyncio.sleep(2)

                if await self._is_auth_wall(page):
                    logger.warning("Auth wall on company page — trying public view")
                    company = await self._extract_public_company(page)
                    if not company.name:
                        # LinkedIn fully blocks company pages without login
                        company.name = "(login required)"
                        company.company_url = url
                    return company

                logger.info("Extracting company data...")
                company = await self._extract_company(page)
                logger.info(f"Company extracted: {company.name}")
                await self._browser.save_session(context, "linkedin")
                return company

            except Exception as page_error:
                logger.error(f"Page operation error: {page_error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                return None
            finally:
                try:
                    await page.close()
                    await context.close()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Company fetch failed: {e}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            return None

    # --- Extraction helpers ---

    async def _is_auth_wall(self, page) -> bool:
        """Check if LinkedIn is showing an auth wall."""
        try:
            # Check page title / h1 for "Join LinkedIn" or "Sign in"
            try:
                h1 = page.locator("h1").first
                h1_text = (await h1.inner_text(timeout=3000)).strip().lower()
                if "join linkedin" in h1_text or "sign in" in h1_text:
                    return True
            except Exception:
                pass

            indicators = [
                'div.authwall-join-form',
                'section.auth-wall',
                'form.join-form',
            ]
            for selector in indicators:
                if await page.locator(selector).count() > 0:
                    return True
        except Exception:
            pass
        return False

    async def _extract_profile(self, page) -> Profile:
        """Extract profile from an authenticated LinkedIn page."""
        profile = Profile()
        profile.profile_url = page.url

        # Name
        try:
            name_el = page.locator("h1").first
            profile.name = (await name_el.inner_text()).strip()
        except Exception:
            pass

        # Headline
        try:
            headline_el = page.locator(
                'div.text-body-medium, div[data-generated-suggestion-target]'
            ).first
            profile.headline = (await headline_el.inner_text()).strip()
        except Exception:
            pass

        # Location
        try:
            loc_el = page.locator(
                'span.text-body-small:has-text(","), '
                'span.text-body-small[class*="inline"]'
            ).first
            profile.location = (await loc_el.inner_text()).strip()
        except Exception:
            pass

        # About
        try:
            about_section = page.locator('#about ~ div, section:has(#about)').first
            about_text = page.locator(
                '#about ~ div span[aria-hidden="true"], '
                'section:has(#about) span[aria-hidden="true"]'
            ).first
            profile.about = (await about_text.inner_text()).strip()
        except Exception:
            pass

        # Current position
        try:
            exp_item = page.locator(
                '#experience ~ div li, section:has(#experience) li'
            ).first
            title_el = exp_item.locator(
                'span[aria-hidden="true"]'
            ).first
            profile.current_title = (await title_el.inner_text()).strip()

            company_el = exp_item.locator(
                'span[aria-hidden="true"]'
            ).nth(1)
            profile.current_company = (await company_el.inner_text()).strip()
        except Exception:
            pass

        # Connections
        try:
            conn_el = page.locator(
                'span:has-text("connection"), span:has-text("follower")'
            ).first
            profile.connections = (await conn_el.inner_text()).strip()
        except Exception:
            pass

        # Skills
        try:
            skills_section = page.locator(
                '#skills ~ div li span[aria-hidden="true"], '
                'section:has(#skills) li span[aria-hidden="true"]'
            )
            count = await skills_section.count()
            for i in range(min(count, 20)):
                skill = (await skills_section.nth(i).inner_text()).strip()
                if skill and skill not in profile.skills:
                    profile.skills.append(skill)
        except Exception:
            pass

        return profile

    async def _extract_public_profile(self, page) -> Profile:
        """Extract what's available from a public (non-logged-in) profile view."""
        profile = Profile()
        profile.profile_url = page.url

        # Try JSON-LD structured data first
        try:
            ld_json = await page.eval_on_selector(
                'script[type="application/ld+json"]',
                "el => el.textContent",
            )
            if ld_json:
                import json
                data = json.loads(ld_json)
                if isinstance(data, list):
                    data = data[0]
                profile.name = data.get("name", "")
                profile.headline = data.get("jobTitle", "") or data.get("description", "")
                loc = data.get("address", {})
                if isinstance(loc, dict):
                    profile.location = loc.get("addressLocality", "")
                elif isinstance(loc, str):
                    profile.location = loc
                # Company from worksFor
                works_for = data.get("worksFor", [])
                if isinstance(works_for, list) and works_for:
                    profile.current_company = works_for[0].get("name", "")
                elif isinstance(works_for, dict):
                    profile.current_company = works_for.get("name", "")
        except Exception:
            pass

        # Fallback to DOM extraction
        if not profile.name or profile.name.lower() in ("join linkedin", "sign in"):
            profile.name = ""
            try:
                name_el = page.locator(
                    'h1.top-card-layout__title, h1[class*="top-card"]'
                ).first
                name = (await name_el.inner_text()).strip()
                if name.lower() not in ("join linkedin", "sign in"):
                    profile.name = name
            except Exception:
                pass

        if not profile.headline:
            try:
                headline_el = page.locator(
                    'h2.top-card-layout__headline, div.top-card-layout__headline'
                ).first
                profile.headline = (await headline_el.inner_text()).strip()
            except Exception:
                pass

        if not profile.location:
            try:
                loc_el = page.locator(
                    'span.top-card__subline-item, '
                    'div.top-card-layout__first-subline span'
                ).first
                profile.location = (await loc_el.inner_text()).strip()
            except Exception:
                pass

        return profile

    async def _extract_people_search(
        self, page, query: str, max_results: int
    ) -> SearchResult:
        """Extract people search results using fast JS extraction."""
        result = SearchResult(query=query, result_type="people")

        # Result count
        try:
            count_el = page.locator("div.search-results-container h2").first
            result.total_count = (await count_el.inner_text()).strip()
        except Exception:
            pass

        # Use fast JS extraction as primary method
        logger.info("People search: using JS extraction")
        result.results = await self._js_extract_people(page, max_results)

        return result

    async def _js_extract_people(self, page, max_results: int) -> list:
        """Extract people results using JavaScript DOM traversal."""
        js = (
            "(maxResults) => {"
            "  const results = [];"
            "  const links = document.querySelectorAll('a[href*=\"/in/\"]');"
            "  const seen = new Set();"
            "  const skip = ['linkedin','sign in','join','linkedin member'];"
            "  for (const link of links) {"
            "    if (results.length >= maxResults) break;"
            "    const href = link.href;"
            "    if (seen.has(href) || !href.includes('/in/')) continue;"
            "    const container = link.closest('li') || link.closest('div') || link.parentElement;"
            "    if (!container) continue;"
            "    const nameText = link.innerText || link.textContent || '';"
            "    const name = nameText.split('\\n').map(t => t.trim()).filter(t => t.length > 0)[0].replace(/\\s+/g, ' ');"
            "    if (!name || name.length < 2) continue;"
            "    if (skip.includes(name.toLowerCase())) continue;"
            "    seen.add(href);"
            "    const allText = Array.from(new Set((container.innerText || '').split('\\n').map(t => t.trim().replace(/\\s+/g, ' ')).filter(t => t && t.length > 1 && t !== name && !name.includes(t))));"
            "    results.push({ name, profile_url: href, headline: allText[0] || '', location: allText[1] || '' });"
            "  }"
            "  return results;"
            "}"
        )
        try:
            return await page.evaluate(js, max_results)
        except Exception as e:
            logger.error(f"JS people extraction failed: {e}")
            return []

    async def _extract_job_search(
        self, page, query: str, max_results: int
    ) -> SearchResult:
        """Extract job search results using fast JS extraction."""
        result = SearchResult(query=query, result_type="jobs")

        # Result count — try multiple selectors
        for count_sel in [
            'div.jobs-search-results-list__subtitle',
            'small.jobs-search-results-list__text',
            'header.jobs-search-results-list__header h2',
            'div.jobs-search-results-list__text',
        ]:
            try:
                count_el = page.locator(count_sel).first
                text = (await count_el.inner_text(timeout=2000)).strip()
                if text:
                    result.total_count = text
                    break
            except Exception:
                continue

        # Use fast JS extraction as primary method
        logger.info("Job search: using JS extraction")
        result.results = await self._js_extract_jobs(page, max_results)

        return result

    async def _js_extract_jobs(self, page, max_results: int) -> list:
        """Extract job results using JavaScript DOM traversal — fast and resilient."""
        js = (
            "(maxResults) => {"
            "  const results = [];"
            "  const seen = new Set();"
            "  const jobLinks = document.querySelectorAll('a[href*=\"/jobs/view/\"]');"
            "  for (const link of jobLinks) {"
            "    if (results.length >= maxResults) break;"
            "    const href = link.href;"
            "    if (seen.has(href)) continue;"
            "    seen.add(href);"
            "    const titleText = link.innerText || link.textContent || '';"
            "    const title = titleText.split('\\n').map(t => t.trim()).filter(t => t.length > 0)[0].replace(/\\s+/g, ' ');"
            "    if (!title || title.length < 3) continue;"
            "    const card = link.closest('li') || link.closest('div') || link.parentElement;"
            "    if (!card) continue;"
            "    const texts = Array.from(new Set((card.innerText || '').split('\\n').map(t => t.trim().replace(/\\s+/g, ' ')).filter(t => t && t.length > 1 && t !== title && !title.includes(t))));"
            "    const job = { title, job_url: href };"
            "    if (texts.length >= 1) job.company = texts[0];"
            "    if (texts.length >= 2) job.location = texts[1];"
            "    const timeEl = card.querySelector('time');"
            "    if (timeEl) job.posted_date = (timeEl.textContent || '').trim();"
            "    else { const ago = texts.find(t => t.includes('ago')); if (ago) job.posted_date = ago; }"
            "    results.push(job);"
            "  }"
            "  if (results.length === 0) {"
            "    const items = document.querySelectorAll('[data-occludable-job-id],[data-job-id]');"
            "    for (const item of items) {"
            "      if (results.length >= maxResults) break;"
            "      const allText = Array.from(new Set((item.innerText || '').split('\\n').map(t => t.trim().replace(/\\s+/g, ' ')).filter(t => t && t.length > 1)));"
            "      if (!allText.length) continue;"
            "      const a = item.querySelector('a');"
            "      const job = { title: allText[0], job_url: a ? a.href : '' };"
            "      if (allText.length >= 2) job.company = allText[1];"
            "      if (allText.length >= 3) job.location = allText[2];"
            "      const timeEl = item.querySelector('time');"
            "      if (timeEl) job.posted_date = (timeEl.textContent || '').trim();"
            "      results.push(job);"
            "    }"
            "  }"
            "  return results;"
            "}"
        )
        try:
            return await page.evaluate(js, max_results)
        except Exception as e:
            logger.error(f"JS job extraction failed: {e}")
            return []

    async def _extract_public_company(self, page) -> Company:
        """Extract company data from a public (non-logged-in) view.

        LinkedIn shows limited data without login but some pages
        have structured data in the page source.
        """
        company = Company()
        company.company_url = page.url

        # Try to extract from structured data (JSON-LD)
        try:
            ld_json = await page.eval_on_selector(
                'script[type="application/ld+json"]',
                "el => el.textContent",
            )
            if ld_json:
                import json
                data = json.loads(ld_json)
                if isinstance(data, list):
                    data = data[0]
                company.name = data.get("name", "")
                company.about = data.get("description", "")
                company.website = data.get("url", "")
                company.employee_count = str(data.get("numberOfEmployees", {}).get("value", ""))
        except Exception:
            pass

        # Try top card elements (sometimes visible without login)
        if not company.name:
            try:
                name_el = page.locator(
                    'h1.top-card-layout__title, h1[class*="org-top-card"]'
                ).first
                company.name = (await name_el.inner_text()).strip()
            except Exception:
                pass

        try:
            tagline_el = page.locator(
                'h2.top-card-layout__headline, p.top-card-layout__headline'
            ).first
            company.tagline = (await tagline_el.inner_text()).strip()
        except Exception:
            pass

        # Industry, size from top card details
        try:
            details = page.locator(
                'div.top-card-layout__first-subline span, '
                'div.org-top-card-summary-info-list span'
            )
            count = await details.count()
            texts = []
            for i in range(count):
                t = (await details.nth(i).inner_text()).strip()
                if t:
                    texts.append(t)
            # Usually: [Industry, Location, Employee count]
            if len(texts) >= 1:
                company.industry = texts[0]
            if len(texts) >= 2:
                company.headquarters = texts[1]
            if len(texts) >= 3:
                company.company_size = texts[2]
        except Exception:
            pass

        return company

    async def _extract_company(self, page) -> Company:
        """Extract company page data."""
        company = Company()
        company.company_url = page.url

        logger.info("Extracting company data (logged-in mode)...")

        # Name
        try:
            name_el = page.locator("h1").first
            company.name = (await name_el.inner_text()).strip()
            logger.info(f"Company name: {company.name}")
        except Exception as e:
            logger.warning(f"Could not extract company name: {e}")

        # Tagline
        try:
            tagline_el = page.locator(
                'p.org-top-card-summary__tagline, '
                'p.top-card-layout__headline'
            ).first
            company.tagline = (await tagline_el.inner_text()).strip()
            logger.info(f"Company tagline: {company.tagline}")
        except Exception as e:
            logger.warning(f"Could not extract company tagline: {e}")

        # About section details
        detail_items = page.locator(
            'dl.overflow-hidden dt, '
            'div.org-page-details__definition-term'
        )
        detail_values = page.locator(
            'dl.overflow-hidden dd, '
            'div.org-page-details__definition-text'
        )

        dt_count = await detail_items.count()
        dd_count = await detail_values.count()

        logger.info(f"Found {dt_count} detail items")

        for i in range(min(dt_count, dd_count)):
            try:
                label = (await detail_items.nth(i).inner_text()).strip().lower()
                value = (await detail_values.nth(i).inner_text()).strip()
                logger.info(f"Company detail: {label} = {value}")

                if "website" in label:
                    company.website = value
                elif "industry" in label:
                    company.industry = value
                elif "company size" in label or "size" in label:
                    company.company_size = value
                elif "headquarter" in label:
                    company.headquarters = value
                elif "founded" in label:
                    company.founded = value
                elif "specialties" in label or "specialities" in label:
                    company.specialties = [
                        s.strip() for s in value.split(",") if s.strip()
                    ]
            except Exception as e:
                logger.warning(f"Error extracting detail {i}: {e}")
                continue

        # About text
        try:
            about_el = page.locator(
                'section.org-about-us-organization-description p, '
                'p[data-test-id="about-us__description"]'
            ).first
            company.about = (await about_el.inner_text()).strip()
            logger.info(f"Company about: {company.about[:100] if company.about else 'None'}...")
        except Exception as e:
            logger.warning(f"Could not extract company about: {e}")

        logger.info(f"Final company object: name={company.name}, industry={company.industry}, headquarters={company.headquarters}")
        return company

    async def cleanup(self):
        if self._own_browser:
            await self._browser.cleanup()
