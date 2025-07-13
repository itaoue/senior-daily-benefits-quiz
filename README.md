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

