# Cookie Export Guide — For Server Users

Your Agent is on a server and can't access your browser directly.
Here's how to export cookies from your local computer — **fastest method first**.

## Method 1: Cookie-Editor Extension (Recommended — 30 seconds per site)

1. Install **Cookie-Editor** for Chrome: https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
   (Also available for Firefox, Edge)

2. Go to the website (e.g. https://x.com) and make sure you're logged in

3. Click the Cookie-Editor icon in your toolbar

4. Click **Export** → **Header String**

5. Paste the result to your Agent

That's it! Your Agent will run:
```bash
scrap-master configure twitter-cookies
```

Both commands use a hidden prompt. For non-interactive automation, send the
same exported value through stdin and add `--stdin`; never place cookies in
the process arguments.

Twitter values saved by Scrap Master are used by `scrap-master doctor` only to
check whether explicit credentials are present. Doctor does not run
`twitter status`. Direct `twitter` commands still require
`TWITTER_AUTH_TOKEN` and `TWITTER_CT0` in their process environment.

Chrome. OpenCLI may use only an existing Chrome session explicitly controlled
cookies.

### Sites to export:

| Site | URL to visit | What to tell Agent |
|------|-------------|-------------------|
| Twitter/X | https://x.com | "Here are my Twitter cookies: [paste]" |

## Method 2: Manual (No extension needed)

1. Open the site in Chrome, make sure you're logged in
2. Press **F12** (or right-click → Inspect)
3. Click the **Network** tab
4. Refresh the page (F5)
5. Click any request in the list
6. In the right panel, scroll to **Request Headers**
7. Find the line starting with `Cookie:`
8. Copy the entire value after `Cookie: `
9. Paste to your Agent
