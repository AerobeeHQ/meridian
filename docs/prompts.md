# Personal Prompts Scratchpad

### Review the todo lists and suggest improvements

Please look for a todo or bug and provide a list of suggested improvements. You can find ideas in todo.md, version-2-roadmap.md, or search the codebase, and find something yourself.

### Find something to do and do it

Please look for a todo or bug and try to address it. You can start with either items in todo.md, version-2-roadmap.md, or search the codebase, and find something yourself. :)

Before modifying any files, create a new branch with prefix `feature/` or `fix/`

Summarise your approach and changes in a new markdown document in the  docs/autopsies folder. (See other md files for example styles)

Limit yourself to using API 2.0 features

### Find something to improve v2

Please look for a todo or bug and try to address it. You can start with either items in todo.md, version-2-roadmap.md, If you don't find anything  there . then search the codebase, and find something yourself. :)

Before modifying any files, create a new branch with prefix feature/ or fix/

Summarise your approach and changes in a new markdown document in the docs/autopsies folder. (See other md files for example styles)

Limit yourself to using Analytics API 2.0 or Reactor API features

Do not commit any changes.

### Suggested Improvements

### Code Review

Please review the code you are about to merge, looking for bugs, and opportunities to simplify the code, cleanup dead end logic, or out of date comments, or out of data documentation. Do not edit old autopsies or old plans.

### Documentation Review

Please review the documentation in this project, looking for inconsistencies, outdated information, or opportunities to improve clarity and readability. Ensure that the documentation aligns with the code changes and provides accurate information for users.

### Product Brochure Site

Please create a product brochure site for the project in a new folder named `/site` in the root of the project. The site will be hosted using Cloudflare Pages. Please provide separate instructions for how to run the site locally as well as how to deploy the site to Cloudflare Pages. 

The brochure site should include information about the project, its features, and how to get started. Please use the staticninja static site generator. I will run the build script locally, and then push/publish the compiled files to Cloudflare. There is no need to run the build procedure on Cloudflare. 

Please ensure that the site is visually appealing. All content should be on a single page, and the site should be responsive and mobile-friendly. You can use any design or layout you think is appropriate, but it should be easy to navigate and understand. The site should have a clean and modern design, with clear and concise language, and easy-to-read typography.

Please create a new branch for the site and submit a pull request. Please include a screenshot of the site in the pull request. Please generate an autopsy document in the docs/autopsies folder summarising your approach and any challenges you faced during the development of the site. (See other md files for example styles)

### Multisite Feature

Reorganise the site structure so that the Codex promotion site is available at the root of the domain (ie: http://localhost:5010, or https://codex.maxisdev.com -- noting that the public facing site is served via docker, and exposed using a cloudflare tunnel), then subfolders for each client configuration (`/maxis`, `/origin`, `/coles`, `/jetstar`, `/etc`). I currently have seperate config.<client-name>.json file for each client, but I think it would be better to have a single config file with multiple client configurations, and then use the URL path to determine which client configuration to use.

The demo links in the brochure site should only link to the `/maxis` site. I will use Cloudflare WAF rules to password protect the other client sites, and share the credentials with the relevant stakeholders.

If you think it is appropriate, or a better architecture then happy for you to move/integrate thee current `/site` folder into the `/app` folder.

Please stop and ask me if you have any questions.

### Image Carousel

Please add an image carousel to the promotional site, using screenshots that I've taken of the Codex application . The carousel should be a 60 second slideshow of images from the `site/static/img/screenshots` folder.

Please inspect the images and rename each to something meaningful.

Please ensure that the images are high resolution and optimized for web use. Consider using a tool like ImageOptim to reduce file size without sacrificing quality.

Please also consider adding captions or descriptions to each image to provide context and improve accessibility.

### Product Brochure Site

Please create a product brochure site for the project in a new folder named `/site` in the root of the project. The site will be hosted using Cloudflare Pages. Please provide separate instructions for how to run the site locally as well as how to deploy the site to Cloudflare Pages. 

The brochure site should include information about the project, its features, and how to get started. Please use the staticninja static site generator. I will run the build script locally, and then push/publish the compiled files to Cloudflare. There is no need to run the build procedure on Cloudflare. 

Please ensure that the site is visually appealing. All content should be on a single page, and the site should be responsive and mobile-friendly. You can use any design or layout you think is appropriate, but it should be easy to navigate and understand. The site should have a clean and modern design, with clear and concise language, and easy-to-read typography.

Please create a new branch for the site and submit a pull request. Please include a screenshot of the site in the pull request. Please generate an autopsy document in the docs/autopsies folder summarising your approach and any challenges you faced during the development of the site. (See other md files for example styles)

