# How to setup a GitHub App for prbot

## Create a new GitHub App

1. Go to your user/organisation profile (https://github.com/settings/profile)
2. Access the "Developer Settings" in the right sidebar (https://github.com/settings/apps)
3. In the "GitHub Apps" section, press the "New GitHub App" button (https://github.com/settings/apps/new)
4. Fill in some of the fields.
    - GitHub App Name: Your app name (you can put anything you want)
    - Homepage URL: A link to your app page (you can put anything you want)
    - Webhook / Active: Tick the box if not already ticked.
    - Webhook / Webhook URL: URL to your bot `/webhook` path.
        - If the bot lives at `https://my-bot.example.org`, enter `https://my-bot.example.org/webhook`
    - Webhook / Webhook secret: Put something safe to make sure GitHub generated the events.
        - You can generate something using this for example: https://acte.ltd/utils/randomkeygen
        - GitHub will never show the secret again, make sure you keep it somewhere safe.
5. Write down some parameters.
    - The Client ID
6. Generate a private key (at the bottom of the page) by clicking on the button.
    - It will download a PEM file with a name looking like "[your-bot-name].[the-date-of-generation].private-key.pem".
7. Set the app permissions in the "Permissions & events" section.
    - In "Repository permissions":
        - Set "Checks" to "Read and write" (to read/set checks)
        - Set "Commit statuses" to "Read and write" (to read/set commit statuses)
        - Set "Contents" to "Read and write" (to merge pull requests)
        - Set "Issues" to "Read and write" (to read/set labels)
        - Set "Pull requests" to "Read and write" (to read/post/edit comments, get pulls info)
    - In "Subscribe to events":
        - Tick "Check suite"
        - Tick "Issue comment"
        - Tick "Pull request"
        - Tick "Pull request review"
    - Then "Save changes"

## Install the application to its first repository

1. Go to your user/organisation profile (https://github.com/settings/profile)
2. Access the "Developer Settings" in the right sidebar (https://github.com/settings/apps)
3. In the "GitHub Apps" section, go to your bot app page (https://github.com/settings/apps/[your-bot-name])
4. Go to the "Install App" section (https://github.com/settings/apps/[your-bot-name]/installations)
5. Press the "Install" button on the right of your username/organization.
6. On the next screen, choose "Only select repositories", and choose the repositories you want, then press "Install".

## Optional: Install the application to a new repository

1. Go to your user/organisation profile (https://github.com/settings/profile)
2. Access the "Developer Settings" in the right sidebar (https://github.com/settings/apps)
3. In the "GitHub Apps" section, go to your bot app page (https://github.com/settings/apps/[your-bot-name])
4. Go to the "Install App" section (https://github.com/settings/apps/[your-bot-name]/installations)
5. Click on the "Settings" icon.
6. Then, in the "Repository access" section, click on the "Select repositories" button to choose the repositories you want.
    - Don't forget to save.
