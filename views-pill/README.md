# views-pill

Tiny Vercel function that draws the "Profile Views" pill for the profile README and
counts a view every time the README is opened.

## Deploy (one time)

1. vercel.com > Add New > Project > import the profile repository.
2. Set **Root Directory** to `views-pill`. Framework Preset: **Other**.
3. Set the project name to `dev-profile-views` (so the address is `https://dev-profile-views.vercel.app`).
4. Deploy, then open `https://dev-profile-views.vercel.app/api/views?theme=dark`. The pill should appear.

The README already points at that address. If Vercel gives you a different one, change it in the README.

Optional: add an environment variable `GH_USERNAME` if the GitHub username ever changes.
