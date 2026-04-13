# Serendipity Massage Therapy — SEO Issues Brief
**Prepared:** 2026-04-12 | **For:** SEO Machine Project
**Site:** serendipitymassage.co.uk (staging: staging2.serendipitymassage.co.uk)

---

## Already Fixed (do not re-do)

- **JSON-LD `telephone` field HTML anchor tags** — all 39 CPT pages (seo_service, seo_location, seo_problem) had `<a href="tel:...">0141 673 6630</a>` inside JSON-LD string values, breaking JSON parsing. Fixed 2026-04-12. All CPT schema now parses correctly.

---

## Outstanding Issues

### Priority 1 — Critical (blocking rich results / live launch)

#### 1.1 No SEO plugin installed
No Yoast, Rank Math, or AIOSEO is active. Nothing is automatically generating meta titles, meta descriptions, or Open Graph tags on the standard WordPress pages. Every standard page is effectively invisible to social sharing and missing proper search snippets.

**Recommended fix:** Install Rank Math Free (preferred) or Yoast SEO. Configure site-wide defaults.

#### 1.2 Site title is staging placeholder
WordPress site title is currently `Staging SDY`. This bleeds into every page `<title>` tag (e.g. `Services – Staging SDY`). Must be corrected to `Serendipity Massage Therapy & Wellness` before go-live.

**Fix:** Settings → General → Site Title in WP admin.

---

### Priority 2 — High (significant SEO impact)

#### 2.1 No meta descriptions on standard pages
None of the following pages have a meta description:

| Page | URL slug | Suggested description |
|---|---|---|
| Home | `/` | ~155 chars about Serendipity Massage Therapy & Wellness, Glasgow city centre, book online |
| Services | `/services/` | Overview of all treatments offered — Thai, oil, hot stone, sports, aromatherapy, facial |
| About Us | `/about-us/` | About the therapist / studio background |
| Contact Us | `/contact-us/` | How to get in touch, address, phone, booking |
| Find Us | `/find-us/` | Location, directions, transport links |

#### 2.2 Thin meta descriptions on CPT pages
Meta descriptions on seo_service and seo_location pages exist but are placeholder-thin (8–21 characters — effectively just the service/location name with nothing descriptive). Each page needs a 120–160 character description.

- **seo_service** (10 pages): each needs a unique description referencing the specific treatment and Glasgow/Hope Street location
- **seo_location** (16 pages): each needs a unique description referencing Thai massage in that specific Glasgow neighbourhood
- **seo_problem** (13 pages): check — may also have thin descriptions

#### 2.3 No JSON-LD schema on standard pages
None of the standard WP pages have any structured data. Recommended schema per page:

| Page | Schema type(s) recommended |
|---|---|
| **Home** | `LocalBusiness` (with name, address, telephone, openingHours, geo, url, sameAs for socials) |
| **Services** | `ItemList` listing each service with URL + `Service` type |
| **About Us** | `Person` or `Organization` |
| **Contact Us** | `LocalBusiness` with full address / phone / opening hours |
| **Find Us** | `LocalBusiness` with `hasMap`, address, `geo` coordinates |
| **Book Now** | `Service` with `potentialAction` → `ReserveAction` |

**NAP for schema (confirmed correct):**
```
Name: Serendipity Massage Therapy & Wellness
Address: Floor 1, Suite 48-50, Central Chambers, 93 Hope Street, Glasgow G2 6LD
Telephone: 0141 673 6630
URL: https://serendipitymassage.co.uk
```

#### 2.4 Missing H1 on Services page
The `/services/` page has no H1 element. This is a significant on-page signal. Should be something like `Our Massage Treatments in Glasgow` or `Massage Services — Serendipity Therapy & Wellness`.

---

### Priority 3 — Medium

#### 3.1 No Open Graph or Twitter Card meta tags anywhere
No `og:title`, `og:description`, `og:image`, `twitter:card` etc. on any page. Social sharing will produce unformatted previews with no image. An SEO plugin will handle this once configured.

#### 3.2 `Article` schema type on location pages
The seo_location pages use `Article` as one of their schema types. Location landing pages are not articles — `WebPage` with `about` pointing to the location, or `LocalBusiness` with `areaServed`, would be semantically correct. Low priority but worth correcting in the CPT template.

#### 3.3 Canonical URLs on CPT pages point to staging domain
All CPT pages currently have canonicals set to `staging2.serendipitymassage.co.uk`. These must resolve to the live domain after go-live. If using a SEO plugin this may be managed automatically; otherwise verify each page post-launch.

---

## Reference — Current CPT Inventory (Staging)

| Post type | Count | Has schema | Schema types present |
|---|---|---|---|
| seo_service | 10 | Yes (now valid) | Service, FAQPage, LocalBusiness |
| seo_location | 16 | Yes (now valid) | Article\*, FAQPage, LocalBusiness |
| seo_problem | 13 | Yes (now valid) | (check per page) |
| Standard pages | 5 | **No** | None |

\* Article type on location pages — see 3.2 above.

---

## Notes for SEO Machine Project

- The CPT page templates (seo_service, seo_location, seo_problem) are Elementor-based. Schema is embedded as an HTML widget containing a `<script type="application/ld+json">` block inside the `_elementor_data`. Any template-level schema changes need to be pushed to all existing posts individually (39 posts), or done via the template and regenerated.
- REST API calls from an external dev machine IP are blocked by SiteGround bot protection. All write operations to staging must go via Playwright MCP (logged-in browser, same-origin fetch). Direct `curl` or external API calls will be rejected.
- Live site credentials and server details are in `serendipitymassage.co.uk-svr-details.txt` in the Serendipity project folder.
