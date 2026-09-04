# Senior Daily Benefits Quiz

A lead generation landing page designed to help seniors discover benefits they may be missing.

## Features

- Interactive 4-question quiz
- Email collection with BigMailer API integration
- NewsBreak pixel tracking for advertising
- Responsive design for all devices
- Complete legal pages (Privacy Policy, Terms & Conditions)

## Deployment

This application is designed to be deployed on Railway with zero configuration.

### Environment Variables

Set the following environment variables in your Railway project:

```
BIGMAILER_API_KEY=your_api_key_here
BIGMAILER_BRAND_ID=your_brand_id_here
BIGMAILER_LIST_ID=your_list_id_here
FLASK_ENV=production
PORT=5000
```

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables in a `.env` file

3. Run the application:
```bash
python src/main.py
```

The application will be available at `http://localhost:5000`

## API Endpoints

- `GET /` - Main quiz page
- `POST /api/submit-email` - Submit email and quiz answers
- `GET /api/health` - Health check endpoint
- `GET /about.html` - About page
- `GET /privacy-policy.html` - Privacy policy
- `GET /terms-conditions.html` - Terms and conditions
- `GET /contact.html` - Contact page

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Email Service**: BigMailer API
- **Tracking**: NewsBreak Pixel
- **Deployment**: Railway

## License

Private - All rights reserved

## Articles section

Articles live in `content/articles/*.md` (front matter + Markdown).
`tools/build_articles.py` turns them into HTML under `src/static/articles/`.
Railway runs the builder automatically at deploy time (see `railway.json`), so
only the `.md` files need to be committed. Partner/affiliate blocks and links are
defined once in `SPONSORS` inside `tools/build_articles.py`.

To preview locally: `python tools/build_articles.py && python src/main.py`

## Environment variables (set in Railway → Variables)

- `BIGMAILER_API_KEY` – required for quiz email capture
- `BIGMAILER_BRAND_ID`, `BIGMAILER_LIST_ID` – optional overrides
- `SECRET_KEY` – Flask session secret

## Newsletter

Each issue is a JSON file in `content/newsletters/` (subject, greeting, story slugs,
sponsor keys, quiz, roundup). Build the email HTML + plain-text with:

    python tools/build_newsletter.py content/newsletters/2026-09-08.json

Output lands in `dist/newsletters/<date>.html`. Paste the HTML into BigMailer
(replace `{{unsubscribe_link}}` / `{{web_version_link}}` with BigMailer's merge tags
if they differ). Every link carries `utm_campaign=<date>` so you can see which
story and sponsor slot drove clicks.

## Everflow offer catalog

`tools/everflow_offers.py` pulls the offers you can run from an Everflow network
(affiliate API) into `content/offers/everflow.json` and prints what changed since
the last pull (new offers, removed offers, payout or status changes). Set
`EVERFLOW_API_KEY` (Affiliate Portal → Account → API) in `~/.zshrc`, then:

    python tools/everflow_offers.py            # refresh the catalog
    python tools/everflow_offers.py --all      # include offers that still need approval
    python tools/everflow_offers.py --diff     # preview changes without overwriting
    python tools/everflow_offers.py --csv      # also write dist/offers/everflow.csv

Use the catalog's `tracking_url` and description when adding a block to `SPONSORS`
in `tools/build_articles.py`.
