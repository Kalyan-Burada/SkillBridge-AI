"""
knowledge_base.py  —  Skill knowledge base for Career Copilot.

Design principles
──────────────────
• Covers a broad range of domains: software, data, cloud, devops, product,
  business, finance, healthcare, design, marketing, legal, supply chain, etc.
• The "default" entry is used for any skill not explicitly listed, so the
  system always generates useful advice regardless of domain.
• get_skill_knowledge() uses fuzzy matching (partial substring) so minor
  wording variations still find the correct entry.
• get_all_knowledge_texts() exports all entries for FAISS indexing.
"""
from __future__ import annotations

SKILL_KNOWLEDGE_BASE: dict = {

    # ── Software: Frontend ────────────────────────────────────────────────────
    "react": {
        "description": "React is a JavaScript library for building fast, interactive UIs using a component-based architecture.",
        "learning_resources": [
            "Complete the official React documentation tutorial (react.dev)",
            "Build projects with React hooks, context API, and React Router",
            "Study state management with Redux Toolkit or Zustand",
            "Learn testing with React Testing Library and Jest",
        ],
        "project_ideas": [
            "Build a real-time dashboard with dynamic charts (React + Recharts)",
            "Create a full-stack e-commerce app with cart, auth, and checkout",
            "Develop a Kanban board with drag-and-drop (react-dnd)",
            "Build a social-feed with infinite scroll and real-time updates",
        ],
        "career_paths": ["Frontend Developer", "React Developer", "Full-Stack Engineer"],
        "estimated_time": "3-5 months for production-ready proficiency",
    },
    "angular": {
        "description": "Angular is a TypeScript-based framework by Google for building scalable single-page applications.",
        "learning_resources": [
            "Complete the official Angular tutorial (angular.io)",
            "Master RxJS observables, pipes, and reactive forms",
            "Study lazy loading, route guards, and Angular modules",
            "Learn NgRx for state management and Angular Material for UI",
        ],
        "project_ideas": [
            "Build an enterprise admin dashboard with role-based access control",
            "Create a real-time chat app (Angular + WebSockets)",
            "Develop a CRM with complex forms and data grids",
            "Build a movie discovery app with search and filters",
        ],
        "career_paths": ["Angular Developer", "Frontend Engineer", "Enterprise UI Developer"],
        "estimated_time": "4-6 months for intermediate proficiency",
    },
    "vue": {
        "description": "Vue.js is a progressive JavaScript framework known for its gentle learning curve and flexibility.",
        "learning_resources": [
            "Complete the official Vue 3 tutorial with Composition API",
            "Study Pinia for state management and Vue Router",
            "Learn Nuxt.js for SSR and static generation",
            "Practice with Vuetify or PrimeVue component libraries",
        ],
        "project_ideas": [
            "Build a recipe sharing app with CRUD and user profiles",
            "Create a Kanban board with drag-and-drop using Vue + Pinia",
            "Develop a blog with Nuxt.js and markdown support",
        ],
        "career_paths": ["Vue Developer", "Frontend Engineer", "Full-Stack Developer"],
        "estimated_time": "3-4 months for production-ready skills",
    },
    "javascript": {
        "description": "JavaScript is the core language of the web, essential for frontend interactivity and backend (Node.js).",
        "learning_resources": [
            "Master ES6+ features: arrow functions, destructuring, async/await, modules",
            "Study 'You Don't Know JS' series by Kyle Simpson",
            "Learn DOM manipulation, event handling, and browser APIs",
            "Practice algorithmic problems on LeetCode with JavaScript",
        ],
        "project_ideas": [
            "Build a vanilla JS SPA without any framework",
            "Create a browser-based game using Canvas API",
            "Develop a Chrome extension with content scripts",
        ],
        "career_paths": ["Frontend Developer", "Full-Stack Developer", "JavaScript Engineer"],
        "estimated_time": "2-4 months for solid intermediate skills",
    },
    "typescript": {
        "description": "TypeScript adds static typing to JavaScript, enabling better tooling and large-scale development.",
        "learning_resources": [
            "Complete the TypeScript Handbook (typescriptlang.org)",
            "Study generics, mapped types, conditional types, utility types",
            "Practice converting JS projects to TypeScript with strict mode",
            "Learn TypeScript with React or Angular",
        ],
        "project_ideas": [
            "Migrate an existing JS project to TypeScript with strict mode",
            "Build a type-safe REST API client with generics and Zod",
            "Create a typed design-system component library",
        ],
        "career_paths": ["Frontend Engineer", "Full-Stack Developer", "TypeScript Developer"],
        "estimated_time": "2-3 months if already proficient in JavaScript",
    },
    "css": {
        "description": "CSS controls visual presentation: layout, colour, typography, and animations.",
        "learning_resources": [
            "Master Flexbox and CSS Grid thoroughly",
            "Study responsive design with media queries",
            "Learn CSS animations, transitions, and keyframes",
            "Practice with Tailwind CSS or CSS Modules",
        ],
        "project_ideas": [
            "Build a fully responsive portfolio with advanced animations",
            "Recreate popular site layouts pixel-perfect",
            "Create a CSS-only component library",
        ],
        "career_paths": ["Frontend Developer", "UI Developer", "UX Engineer"],
        "estimated_time": "2-3 months for advanced proficiency",
    },
    "html": {
        "description": "HTML is the standard markup language providing structure and semantic meaning to web content.",
        "learning_resources": [
            "Master semantic HTML5 elements (article, section, nav, aside)",
            "Study web accessibility (WCAG, ARIA attributes)",
            "Learn SEO best practices and structured data",
            "Practice with HTML forms and multimedia elements",
        ],
        "project_ideas": [
            "Build an accessible multi-page site following WCAG 2.1 AA",
            "Create a documentation site with semantic structure",
            "Build interactive forms with client-side validation",
        ],
        "career_paths": ["Frontend Developer", "Web Developer", "Accessibility Specialist"],
        "estimated_time": "1-2 months for advanced proficiency",
    },

    # ── Software: Backend ─────────────────────────────────────────────────────
    "python": {
        "description": "Python is a versatile language used in web development, data science, automation, and AI/ML.",
        "learning_resources": [
            "Master Python fundamentals: data structures, OOP, decorators, generators",
            "Learn Django or FastAPI for web application development",
            "Study testing with pytest and type hints with mypy",
            "Practice data manipulation with pandas and numpy",
        ],
        "project_ideas": [
            "Build a REST API with FastAPI including JWT auth and DB models",
            "Create a web scraper with data pipeline and automated reporting",
            "Develop a task automation tool for workflow optimisation",
        ],
        "career_paths": ["Python Developer", "Backend Engineer", "Data Engineer", "ML Engineer"],
        "estimated_time": "3-5 months for intermediate proficiency",
    },
    "node.js": {
        "description": "Node.js is a JavaScript runtime for building scalable server-side applications with non-blocking I/O.",
        "learning_resources": [
            "Master Express.js or Fastify for REST API development",
            "Study async patterns: callbacks, promises, async/await, event loop",
            "Learn database integration (Prisma/Sequelize for PostgreSQL, Mongoose for MongoDB)",
            "Practice building microservices with message queues",
        ],
        "project_ideas": [
            "Build a RESTful API with authentication, rate limiting, and caching",
            "Create a real-time notification system using Socket.io",
            "Develop a file upload service with cloud storage integration",
        ],
        "career_paths": ["Backend Developer", "Node.js Developer", "Full-Stack Engineer"],
        "estimated_time": "3-5 months for production-ready skills",
    },
    "java": {
        "description": "Java is a robust, object-oriented language widely used in enterprise backend systems and Android.",
        "learning_resources": [
            "Master OOP principles, generics, and Java collections framework",
            "Learn Spring Boot for RESTful API and microservices development",
            "Study JUnit, Mockito for testing, and Maven/Gradle for builds",
            "Practice concurrency: threads, ExecutorService, CompletableFuture",
        ],
        "project_ideas": [
            "Build a Spring Boot microservice with REST API and PostgreSQL",
            "Create a multi-threaded task processing system",
            "Develop a Spring Security–protected authentication service",
        ],
        "career_paths": ["Java Developer", "Backend Engineer", "Enterprise Architect"],
        "estimated_time": "4-6 months for production-level Spring Boot",
    },
    "sql": {
        "description": "SQL is the standard language for managing and querying relational databases.",
        "learning_resources": [
            "Master JOINs, subqueries, CTEs, and window functions",
            "Study query optimisation, indexing, and execution plans",
            "Learn database design: normalisation, ERD diagrams, constraints",
            "Practice on LeetCode SQL and real-world datasets",
        ],
        "project_ideas": [
            "Design and implement a normalised schema for an e-commerce system",
            "Build complex analytical queries for BI reporting",
            "Optimise slow queries in an existing database",
        ],
        "career_paths": ["Database Developer", "Data Analyst", "Backend Developer", "Data Engineer"],
        "estimated_time": "2-4 months for advanced proficiency",
    },
    "rest api": {
        "description": "REST API design involves creating scalable, stateless web services following HTTP standards.",
        "learning_resources": [
            "Study RESTful principles: resources, HTTP methods, status codes",
            "Learn API documentation with OpenAPI/Swagger",
            "Master authentication: OAuth 2.0, JWT, API keys",
            "Study versioning, pagination, filtering, and error handling",
        ],
        "project_ideas": [
            "Design and build a REST API for a task management application",
            "Create an API gateway with rate limiting and auth",
            "Build a public API with documentation and developer portal",
        ],
        "career_paths": ["Backend Developer", "API Developer", "Full-Stack Engineer"],
        "estimated_time": "2-3 months for production-quality API design",
    },
    "graphql": {
        "description": "GraphQL is a query language for APIs letting clients request exactly the data they need.",
        "learning_resources": [
            "Master schema design: types, queries, mutations, subscriptions",
            "Learn Apollo Client and Apollo Server or Yoga",
            "Study DataLoader for batching and N+1 problem prevention",
        ],
        "project_ideas": [
            "Build a GraphQL API for a social media platform with subscriptions",
            "Migrate an existing REST API to GraphQL",
            "Create a federated GraphQL gateway for microservices",
        ],
        "career_paths": ["Backend Developer", "Full-Stack Engineer", "API Architect"],
        "estimated_time": "2-4 months for production usage",
    },

    # ── Software: Cloud / DevOps ──────────────────────────────────────────────
    "aws": {
        "description": "Amazon Web Services is the leading cloud platform (and cloud platforms) offering cloud computing, storage, databases, and AI/ML services.",
        "learning_resources": [
            "Study for AWS Solutions Architect Associate certification",
            "Master core services: EC2, S3, RDS, Lambda, API Gateway, CloudFront",
            "Learn Infrastructure as Code with CloudFormation or Terraform",
            "Practice with AWS Free Tier hands-on labs",
        ],
        "project_ideas": [
            "Build a serverless API with Lambda, API Gateway, and DynamoDB",
            "Deploy a scalable web app with ECS and RDS",
            "Build an event-driven architecture with SQS, SNS, and Lambda",
        ],
        "career_paths": ["Cloud Engineer", "Solutions Architect", "DevOps Engineer"],
        "estimated_time": "4-6 months for associate-level proficiency",
    },
    "microsoft azure": {
        "description": "Microsoft Azure is a comprehensive cloud platform (and cloud platforms) for building, deploying cloud computing and managing applications.",
        "learning_resources": [
            "Study for Azure Fundamentals (AZ-900) certification",
            "Master Azure App Service, Functions, SQL, Blob Storage",
            "Learn Azure DevOps pipelines and Bicep/ARM templates",
            "Practice with Azure free tier and Microsoft Learn modules",
        ],
        "project_ideas": [
            "Build a serverless app with Azure Functions and Cosmos DB",
            "Create a CI/CD pipeline with Azure DevOps and staging environments",
            "Deploy a containerised app with AKS",
        ],
        "career_paths": ["Azure Cloud Engineer", "Solutions Architect", "DevOps Engineer"],
        "estimated_time": "4-6 months for associate certification",
    },
    "docker": {
        "description": "Docker enables containerisation of applications for consistent deployment across environments.",
        "learning_resources": [
            "Master Dockerfile creation, multi-stage builds, and image optimisation",
            "Study Docker Compose for multi-container orchestration",
            "Learn container networking, volumes, and security best practices",
        ],
        "project_ideas": [
            "Containerise a full-stack app (frontend + backend + database)",
            "Build a microservices architecture with Docker Compose",
            "Create a CI/CD pipeline that builds, tests, and deploys images",
        ],
        "career_paths": ["DevOps Engineer", "Platform Engineer", "Backend Developer"],
        "estimated_time": "2-3 months for production usage",
    },
    "kubernetes": {
        "description": "Kubernetes is an open-source platform for automating container deployment, scaling, and management.",
        "learning_resources": [
            "Study architecture: pods, services, deployments, ingress, ConfigMaps",
            "Prepare for CKA (Certified Kubernetes Administrator)",
            "Learn Helm charts for package management",
            "Practice with Minikube or Kind locally",
        ],
        "project_ideas": [
            "Deploy a microservices app on Kubernetes with auto-scaling",
            "Build a GitOps CI/CD pipeline with ArgoCD",
            "Create Helm charts for your application stack",
        ],
        "career_paths": ["DevOps Engineer", "Platform Engineer", "SRE", "Cloud Architect"],
        "estimated_time": "4-6 months for intermediate proficiency",
    },
    "ci/cd": {
        "description": "CI/CD automates the build, test, and deployment pipeline for faster, reliable software delivery.",
        "learning_resources": [
            "Master GitHub Actions, GitLab CI, or Jenkins pipeline configuration",
            "Study deployment strategies: blue-green, canary, rolling updates",
            "Learn Infrastructure as Code: Terraform, Ansible, or Pulumi",
        ],
        "project_ideas": [
            "Build a complete CI/CD pipeline with automated testing and staging",
            "Create a multi-environment deployment system (dev/staging/prod)",
            "Implement automated security scanning (SAST/DAST) in the pipeline",
        ],
        "career_paths": ["DevOps Engineer", "SRE", "Platform Engineer", "Release Manager"],
        "estimated_time": "3-4 months for production pipeline management",
    },
    "git": {
        "description": "Git is the industry-standard distributed version control system.",
        "learning_resources": [
            "Master branching strategies: GitFlow, trunk-based development",
            "Study rebasing, cherry-picking, bisect, and stash",
            "Learn GitHub/GitLab features: PRs, code reviews, CI integration",
        ],
        "project_ideas": [
            "Contribute to an open-source project using proper Git workflow",
            "Set up branch protection rules and automated PR checks",
            "Manage a monorepo with multiple packages",
        ],
        "career_paths": ["Software Developer", "DevOps Engineer", "Technical Lead"],
        "estimated_time": "2-4 weeks for advanced proficiency",
    },

    # ── Software: Data & ML ───────────────────────────────────────────────────
    "machine learning": {
        "description": "ML is a subset of AI focused on algorithms that learn from data without explicit programming.",
        "learning_resources": [
            "Complete Andrew Ng's Machine Learning Specialization (Coursera)",
            "Study Hands-On Machine Learning with Scikit-Learn and TensorFlow",
            "Learn statistical foundations: linear algebra, probability, calculus",
            "Practice on Kaggle competitions and real datasets",
        ],
        "project_ideas": [
            "Build a fraud detection system",
            "Create a customer churn prediction model",
            "Develop a sentiment analysis tool",
            "Implement a time-series forecasting model",
        ],
        "career_paths": ["ML Engineer", "Data Scientist", "AI Researcher"],
        "estimated_time": "4-8 months for intermediate skills",
    },
    "artificial intelligence": {
        "description": "AI involves simulation of human intelligence in machines, including learning, reasoning, and self-correction.",
        "learning_resources": [
            "Complete Andrew Ng's Deep Learning Specialization",
            "Read 'Artificial Intelligence: A Modern Approach' by Russell & Norvig",
            "Study transformer architectures and LLM fundamentals",
            "Practice with Kaggle and open datasets",
        ],
        "project_ideas": [
            "Build a chatbot using NLP and retrieval-augmented generation",
            "Create an image classification system with CNNs",
            "Develop a recommendation system",
        ],
        "career_paths": ["AI Engineer", "ML Engineer", "Data Scientist", "AI Product Manager"],
        "estimated_time": "6-12 months for foundational proficiency",
    },
    "data analytics": {
        "description": "Data analytics involves examining datasets to draw conclusions and support decision-making.",
        "learning_resources": [
            "Master SQL for data querying and manipulation",
            "Learn Python libraries: pandas, numpy, matplotlib, seaborn",
            "Study Tableau or Power BI for visualisation",
            "Take Google Data Analytics Professional Certificate",
        ],
        "project_ideas": [
            "Analyse sales data to identify trends",
            "Create interactive business-metrics dashboards",
            "Perform cohort analysis for user retention",
        ],
        "career_paths": ["Data Analyst", "Business Analyst", "Analytics Manager"],
        "estimated_time": "3-6 months for job-ready skills",
    },
    "power bi": {
        "description": "Power BI is Microsoft's business analytics tool for interactive dashboards, visualizations, and data visualisations.",
        "learning_resources": [
            "Complete the PL-300 (Power BI Data Analyst) certification path",
            "Master DAX formulas for calculated columns and measures",
            "Study Power Query (M language) for data transformation",
            "Learn data modelling: star schema, relationships, row-level security",
        ],
        "project_ideas": [
            "Build an executive sales dashboard with drill-through reports",
            "Create a customer analytics report with RFM segmentation",
            "Develop a financial dashboard with YoY comparison and forecasting",
        ],
        "career_paths": ["BI Developer", "Data Analyst", "Business Analyst"],
        "estimated_time": "3-4 months for PL-300 readiness",
    },
    "tableau": {
        "description": "Tableau is a leading data visualisation platform for interactive, shareable dashboards and visualizations.",
        "learning_resources": [
            "Study for Tableau Desktop Specialist or Certified Data Analyst",
            "Master calculated fields, LOD expressions, and table calculations",
            "Learn Tableau Prep for data preparation",
        ],
        "project_ideas": [
            "Build an interactive health data dashboard with maps",
            "Create a marketing analytics dashboard with campaign ROI",
            "Develop a supply-chain visibility dashboard",
        ],
        "career_paths": ["Data Analyst", "BI Developer", "Data Visualisation Specialist"],
        "estimated_time": "2-4 months for certification-ready skills",
    },

    # ── Product & Project Management ──────────────────────────────────────────
    "product management": {
        "description": "Product management involves defining product vision, strategy, and coordinating cross-functional teams.",
        "learning_resources": [
            "Read 'Inspired' by Marty Cagan and 'Continuous Discovery Habits' by Teresa Torres",
            "Take Reforge or Pragmatic Institute courses",
            "Learn analytics tools (Mixpanel, Amplitude)",
            "Study agile and sprint planning methodologies",
        ],
        "project_ideas": [
            "Launch a side project from ideation to MVP",
            "Conduct user research and create a product roadmap",
            "Define and track product KPIs",
        ],
        "career_paths": ["Product Manager", "Senior PM", "VP of Product", "Chief Product Officer"],
        "estimated_time": "6-12 months with hands-on experience",
    },
    "agile": {
        "description": "Agile is an iterative approach to project management emphasising flexibility and collaboration.",
        "learning_resources": [
            "Get Certified Scrum Master (CSM) certification",
            "Study the Agile Manifesto and 12 principles",
            "Learn Scrum, Kanban, and SAFe methodologies",
            "Read 'Scrum: The Art of Doing Twice the Work in Half the Time'",
        ],
        "project_ideas": [
            "Facilitate sprint planning and retrospectives for a real team",
            "Implement a Kanban board and track cycle time",
            "Run a two-week sprint with a side-project team",
        ],
        "career_paths": ["Scrum Master", "Agile Coach", "Product Owner", "Program Manager"],
        "estimated_time": "2-4 months for certification and practice",
    },
    "jira": {
        "description": "Jira is Atlassian's project management tool for agile teams: sprint planning, backlog management, issue tracking.",
        "learning_resources": [
            "Master Jira board configuration: Scrum and Kanban boards",
            "Study JQL (Jira Query Language) for advanced filtering",
            "Learn workflow customisation and automation rules",
        ],
        "project_ideas": [
            "Set up a Jira project with epics, stories, and sprint cycles",
            "Create custom dashboards for team velocity and sprint health",
            "Build Jira automation rules for status transitions",
        ],
        "career_paths": ["Project Manager", "Scrum Master", "Product Manager"],
        "estimated_time": "2-4 weeks for effective daily usage",
    },
    "a/b testing": {
        "description": "A/B testing is a controlled experiment methodology to compare variants using statistical significance.",
        "learning_resources": [
            "Study experimental design: hypothesis formation, sample size, p-values",
            "Learn tools: Optimizely, LaunchDarkly, Statsig, or Google Optimize",
            "Read 'Trustworthy Online Controlled Experiments' by Kohavi et al.",
        ],
        "project_ideas": [
            "Design and run an A/B test on a landing page with conversion tracking",
            "Build a feature-flagging system with gradual rollout",
            "Analyse historical test results and present findings with effect sizes",
        ],
        "career_paths": ["Growth PM", "Data Scientist", "Experimentation Analyst", "Growth Engineer"],
        "estimated_time": "2-3 months for practical experimentation skills",
    },
    "kpi": {
        "description": "Key Performance Indicators are measurable values that demonstrate organisational effectiveness.",
        "learning_resources": [
            "Learn about North Star Metrics and the AARRR framework",
            "Study data visualisation and dashboard creation",
            "Master Excel or Google Sheets for metric tracking",
            "Read 'Lean Analytics' by Alistair Croll",
        ],
        "project_ideas": [
            "Define KPIs for a product or business unit",
            "Build an automated KPI tracking dashboard",
            "Conduct an A/B test and measure impact on KPIs",
        ],
        "career_paths": ["Product Analyst", "Business Analyst", "Product Manager"],
        "estimated_time": "2-3 months for foundational understanding",
    },

    # ── Supply Chain / Operations ─────────────────────────────────────────────
    "supply chain": {
        "description": "Supply chain management coordinates production, inventory, and distribution.",
        "learning_resources": [
            "Study supply chain fundamentals and logistics",
            "Learn demand forecasting and inventory optimisation",
            "Master SAP or Oracle SCM tools",
            "Take APICS CPIM or CSCP certification",
        ],
        "project_ideas": [
            "Optimise inventory levels using forecasting models",
            "Analyse supplier performance and cost drivers",
            "Design a distribution network optimisation model",
        ],
        "career_paths": ["Supply Chain Analyst", "Operations Manager", "Logistics Manager"],
        "estimated_time": "6-9 months for specialised knowledge",
    },
    "demand forecasting": {
        "description": "Demand forecasting uses statistical methods and ML to predict future demand for inventory planning.",
        "learning_resources": [
            "Study time-series models: ARIMA, SARIMA, Prophet, exponential smoothing",
            "Learn ML approaches: XGBoost, LSTM for sequential forecasting",
            "Master evaluation metrics: MAPE, RMSE, MAE, forecast bias",
        ],
        "project_ideas": [
            "Build a demand forecasting model for retail inventory optimisation",
            "Create a multi-product forecasting dashboard with confidence intervals",
            "Compare classical time-series vs ML models on real business data",
        ],
        "career_paths": ["Demand Planner", "Supply Chain Analyst", "Data Scientist"],
        "estimated_time": "3-5 months for production-level forecasting",
    },

    # ── Finance & Accounting ──────────────────────────────────────────────────
    "financial analysis": {
        "description": "Financial analysis evaluates financial data to assess performance and inform investment or operational decisions.",
        "learning_resources": [
            "Study financial statements: income statement, balance sheet, cash flow",
            "Learn financial modelling in Excel (DCF, LBO, comps)",
            "Take CFA Level 1 or a corporate finance course on Coursera",
            "Practice building three-statement models and scenario analysis",
        ],
        "project_ideas": [
            "Build a discounted cash flow valuation model for a public company",
            "Create a financial dashboard tracking revenue, margins, and KPIs",
            "Analyse a company's financial health using ratio analysis",
        ],
        "career_paths": ["Financial Analyst", "Investment Analyst", "FP&A Analyst", "CFO"],
        "estimated_time": "4-6 months for analyst-level proficiency",
    },
    "accounting": {
        "description": "Accounting involves recording, summarising, and reporting financial transactions.",
        "learning_resources": [
            "Study GAAP or IFRS principles and double-entry bookkeeping",
            "Master QuickBooks, Xero, or SAP for bookkeeping",
            "Pursue CPA or ACCA qualification",
            "Learn month-end close processes and reconciliation",
        ],
        "project_ideas": [
            "Set up a full chart of accounts and trial balance for a small business",
            "Build an automated bank reconciliation spreadsheet",
            "Create a budget-vs-actual variance report",
        ],
        "career_paths": ["Accountant", "Controller", "Finance Manager", "CFO"],
        "estimated_time": "Varies: 3-6 months for practical skills, years for certification",
    },

    # ── Healthcare / Clinical ─────────────────────────────────────────────────
    "clinical research": {
        "description": "Clinical research involves designing and conducting studies to evaluate medical interventions.",
        "learning_resources": [
            "Study ICH GCP E6 guidelines and FDA regulations",
            "Learn clinical trial phases (I–IV) and protocol design",
            "Take ACRP or SOCRA certification courses",
            "Study biostatistics: randomisation, blinding, endpoints",
        ],
        "project_ideas": [
            "Design a mock Phase II clinical trial protocol",
            "Create a CDISC SDTM data mapping document",
            "Build a site-selection scoring model for a clinical study",
        ],
        "career_paths": ["Clinical Research Associate", "Clinical Trial Manager", "Regulatory Affairs Specialist"],
        "estimated_time": "6-12 months with hands-on study experience",
    },
    "electronic health records": {
        "description": "EHR systems digitise patient health information and streamline clinical workflows.",
        "learning_resources": [
            "Get certified in Epic, Cerner, or Meditech",
            "Study HL7 FHIR standards for health data interoperability",
            "Learn ICD-10 and SNOMED coding systems",
        ],
        "project_ideas": [
            "Build a FHIR-compliant patient data API",
            "Create a clinical dashboard tracking patient outcomes",
            "Design a data migration plan from legacy EHR to modern system",
        ],
        "career_paths": ["EHR Analyst", "Clinical Informatics Specialist", "Health IT Consultant"],
        "estimated_time": "3-6 months for practical certification",
    },

    # ── Design & Creative ─────────────────────────────────────────────────────
    "ui/ux design": {
        "description": "UI/UX design creates intuitive, user-centred digital experiences combining research, interaction, and visual design.",
        "learning_resources": [
            "Master Figma for wireframing, prototyping, and design systems",
            "Study user research methods: interviews, usability testing, card sorting",
            "Learn interaction design principles and accessibility (WCAG)",
            "Take Google UX Design Certificate on Coursera",
        ],
        "project_ideas": [
            "Redesign a poorly-rated mobile app with a full UX process",
            "Create a design system with components, tokens, and documentation",
            "Conduct usability testing on an existing product and report findings",
        ],
        "career_paths": ["UX Designer", "UI Designer", "Product Designer", "Design Lead"],
        "estimated_time": "4-6 months for portfolio-ready skills",
    },
    "figma": {
        "description": "Figma is the industry-standard collaborative design tool for UI design and prototyping.",
        "learning_resources": [
            "Complete official Figma tutorials and YouTube channels (DesignCourse)",
            "Master components, variants, auto-layout, and design tokens",
            "Study prototyping with interactive components and Smart Animate",
        ],
        "project_ideas": [
            "Design a mobile app from wireframes to high-fidelity prototype",
            "Build a reusable component library with variants and documentation",
            "Create an interactive prototype for user testing",
        ],
        "career_paths": ["UI Designer", "Product Designer", "UX Engineer"],
        "estimated_time": "1-2 months for proficient use",
    },

    # ── Marketing & Growth ────────────────────────────────────────────────────
    "digital marketing": {
        "description": "Digital marketing uses online channels (SEO, paid ads, email, social) to reach and convert customers.",
        "learning_resources": [
            "Get Google Analytics and Google Ads certifications",
            "Study SEO fundamentals: keyword research, on-page, link building",
            "Learn Facebook/Instagram Ads Manager and Meta Business Suite",
            "Take HubSpot's Digital Marketing Certification",
        ],
        "project_ideas": [
            "Run a real Google Ads campaign with a small budget and optimise CTR",
            "Conduct a full SEO audit of a website and implement improvements",
            "Build an email automation sequence with A/B tested subject lines",
        ],
        "career_paths": ["Digital Marketer", "Growth Marketer", "Paid Media Specialist", "CMO"],
        "estimated_time": "3-5 months for practical proficiency",
    },
    "content marketing": {
        "description": "Content marketing creates and distributes valuable content to attract and retain a target audience.",
        "learning_resources": [
            "Study content strategy frameworks: pillar-cluster, topic authority",
            "Master SEO writing: keyword integration, search intent, meta-data",
            "Learn content performance analytics (GA4, Search Console)",
        ],
        "project_ideas": [
            "Build a content calendar and publish 10 SEO-optimised articles",
            "Create a content repurposing workflow from blog to social to email",
            "Measure content ROI using attribution modelling",
        ],
        "career_paths": ["Content Marketer", "Content Strategist", "SEO Specialist", "Content Lead"],
        "estimated_time": "2-4 months for practical content skills",
    },

    # ── Soft / General ────────────────────────────────────────────────────────
    "problem-solving": {
        "description": "Analytical and creative problem-solving for tackling complex, ambiguous challenges.",
        "learning_resources": [
            "Study frameworks: First Principles, 5 Whys, Root Cause Analysis",
            "Practice case interviews and structured thinking (McKinsey, BCG style)",
            "Read 'Thinking, Fast and Slow' by Daniel Kahneman",
        ],
        "project_ideas": [
            "Solve real business problems using structured frameworks",
            "Participate in case competitions or hackathons",
            "Facilitate problem-solving workshops with a team",
        ],
        "career_paths": ["Consultant", "Product Manager", "Engineer", "Analyst"],
        "estimated_time": "Continuous development over career",
    },
    "cross-functional team leadership": {
        "description": "Leading diverse teams across engineering, design, marketing, and other functions toward shared goals.",
        "learning_resources": [
            "Read 'The Five Dysfunctions of a Team' by Patrick Lencioni",
            "Study conflict resolution and stakeholder management",
            "Learn OKR goal-setting frameworks",
        ],
        "project_ideas": [
            "Lead a cross-departmental initiative from kickoff to delivery",
            "Create a communication framework for a distributed team",
            "Mentor junior team members and document the outcomes",
        ],
        "career_paths": ["Team Lead", "Engineering Manager", "Director", "VP"],
        "estimated_time": "Develops over 2-5 years with practice",
    },
    "project management": {
        "description": "Project management plans, organises, and controls resources to achieve specific goals within constraints.",
        "learning_resources": [
            "Study PMP or PRINCE2 certification",
            "Learn project planning tools: MS Project, Asana, Monday.com",
            "Master risk management, stakeholder communication, and change control",
        ],
        "project_ideas": [
            "Manage a real side-project using a full PM methodology",
            "Create a project plan with WBS, GANTT chart, and risk register",
            "Build a retrospective process and track improvement over sprints",
        ],
        "career_paths": ["Project Manager", "Program Manager", "PMO Director"],
        "estimated_time": "3-6 months for entry-level PM certification",
    },
    "communication": {
        "description": "Professional communication covers written, verbal, and presentation skills for clear, effective collaboration.",
        "learning_resources": [
            "Study 'Nonviolent Communication' by Marshall Rosenberg",
            "Practice public speaking via Toastmasters",
            "Take a business writing course (Coursera / LinkedIn Learning)",
        ],
        "project_ideas": [
            "Give a 10-minute technical talk at a meetup or online community",
            "Write weekly technical blog posts and build a portfolio",
            "Lead a retrospective and facilitate team discussion",
        ],
        "career_paths": ["Any senior or leadership role"],
        "estimated_time": "Continuous development",
    },

    # ── Embedded / Hardware ───────────────────────────────────────────────────
    "embedded systems": {
        "description": "Embedded systems programming for microcontrollers, RTOS, and hardware-software interfaces.",
        "learning_resources": [
            "Master C/C++ for embedded targets",
            "Study RTOS concepts: tasks, semaphores, queues (FreeRTOS)",
            "Learn hardware protocols: I2C, SPI, UART, CAN",
            "Practice with Arduino, STM32, or Raspberry Pi",
        ],
        "project_ideas": [
            "Build a sensor data logger with SD card and UART output",
            "Create a real-time motor control system using RTOS",
            "Develop a CAN bus communication node for automotive",
        ],
        "career_paths": ["Embedded Software Engineer", "Firmware Engineer", "Hardware Engineer"],
        "estimated_time": "4-8 months for production firmware skills",
    },

    # ── Legal / Compliance ────────────────────────────────────────────────────
    "compliance": {
        "description": "Compliance ensures organisational processes and policies meet regulatory and legal standards.",
        "learning_resources": [
            "Study relevant regulations: GDPR, HIPAA, SOX, ISO 27001",
            "Take a Certified Compliance & Ethics Professional (CCEP) course",
            "Learn risk assessment and audit procedures",
        ],
        "project_ideas": [
            "Conduct a GDPR gap analysis for a mock organisation",
            "Write a compliance policy document for a specific regulation",
            "Build a risk register and remediation tracking dashboard",
        ],
        "career_paths": ["Compliance Analyst", "Risk Manager", "Regulatory Affairs Specialist", "Chief Compliance Officer"],
        "estimated_time": "4-8 months depending on regulation",
    },

    # ── Foundational Tools / Libraries ────────────────────────────────────────
    "tensorflow": {
        "description": "TensorFlow is an open-source framework for machine learning, artificial intelligence, and deep learning neural networks.",
        "learning_resources": ["TensorFlow documentation", "Deeplearning.ai courses"],
        "project_ideas": ["Train a computer vision model", "Build an NLP classifier"],
        "career_paths": ["ML Engineer", "AI Researcher", "Data Scientist"],
        "estimated_time": "3-6 months",
    },
    "pytorch": {
        "description": "PyTorch is a popular machine learning framework for deep learning, artificial intelligence, and research.",
        "learning_resources": ["PyTorch tutorials", "Fast.ai course"],
        "project_ideas": ["Implement a GAN", "Fine-tune an LLM"],
        "career_paths": ["AI Engineer", "ML Researcher"],
        "estimated_time": "3-6 months",
    },
    "scikit-learn": {
        "description": "Scikit-learn is a fundamental machine learning library in Python for regression, classification, and statistical modeling.",
        "learning_resources": ["Scikit-learn documentation", "Kaggle ML courses"],
        "project_ideas": ["Build a predictive model", "Perform clustering"],
        "career_paths": ["Data Scientist", "Data Analyst"],
        "estimated_time": "1-3 months",
    },
    "pandas": {
        "description": "Pandas is a foundational data analysis and data manipulation library for Python data science workflows.",
        "learning_resources": ["Pandas documentation", "DataCamp courses"],
        "project_ideas": ["Clean a messy dataset", "Perform Exploratory Data Analysis (EDA)"],
        "career_paths": ["Data Analyst", "Data Engineer", "Data Scientist"],
        "estimated_time": "1-2 months",
    },
    "gcp": {
        "description": "Google Cloud Platform (GCP) provides scalable cloud platforms, cloud computing, data analytics, and machine learning infrastructure.",
        "learning_resources": ["GCP Cloud Architect path", "Coursera GCP specializations"],
        "project_ideas": ["Deploy a serverless app", "Build a BigQuery pipeline"],
        "career_paths": ["Cloud Engineer", "Data Engineer"],
        "estimated_time": "3-6 months",
    },
    "databases": {
        "description": "Databases are foundational systems for structured data storage, retrieval, backend management, and full-stack development.",
        "learning_resources": ["SQL fundamentals", "Database design principles"],
        "project_ideas": ["Design a relational schema", "Optimize query performance"],
        "career_paths": ["Backend Engineer", "Database Administrator", "Data Engineer"],
        "estimated_time": "2-4 months",
    },
    "agile": {
        "description": "Agile is an iterative project management and software development methodology focusing on cross-functional teams and fast delivery.",
        "learning_resources": ["Scrum Guide", "Agile Alliance resources"],
        "project_ideas": ["Run a sprint cycle", "Manage backlog in Jira"],
        "career_paths": ["Product Manager", "Scrum Master", "Software Engineer"],
        "estimated_time": "1 month",
    },
    "healthcare": {
        "description": "Healthcare domain expertise involves medical devices, patient outcomes, clinical operations, and regulatory compliance.",
        "learning_resources": ["Healthcare IT certifications", "HIPAA/compliance training"],
        "project_ideas": ["Analyze patient outcome data", "Integrate electronic health records (EHR)"],
        "career_paths": ["Health Informatics", "Medical Product Manager", "Healthcare Analyst"],
        "estimated_time": "6-12 months",
    },

    # ── Default (universal fallback) ──────────────────────────────────────────
    "default": {
        "description": "This is a professional skill relevant to the target role.",
        "learning_resources": [
            "Search for dedicated courses on Coursera, Udemy, or LinkedIn Learning",
            "Read industry-standard books and whitepapers",
            "Join professional communities, forums, and attend conferences",
            "Find a mentor or peer study group in your target field",
        ],
        "project_ideas": [
            "Build a portfolio project that directly demonstrates this skill",
            "Contribute to an open-source project related to this area",
            "Create a case study from your existing work or a personal project",
            "Write a technical article or tutorial to consolidate learning",
        ],
        "career_paths": ["Specialist and senior roles in this domain"],
        "estimated_time": "Varies by skill complexity (3-12 months)",
    },
}


def get_skill_knowledge(skill: str) -> dict:
    """
    Retrieve the knowledge base entry for a skill.

    Matching strategy (in priority order):
      1. Exact lower-case match
      2. Skill is a substring of a KB key (e.g. "rest api design" → "rest api")
      3. KB key is a substring of the skill
      4. Fallback to "default"

    Always returns a valid dict — never raises KeyError.
    """
    skill_lower = skill.lower().strip()

    # 1. Exact
    if skill_lower in SKILL_KNOWLEDGE_BASE:
        return SKILL_KNOWLEDGE_BASE[skill_lower]

    # 2 & 3. Partial match
    for key in SKILL_KNOWLEDGE_BASE:
        if key == "default":
            continue
        if key in skill_lower or skill_lower in key:
            return SKILL_KNOWLEDGE_BASE[key]

    return SKILL_KNOWLEDGE_BASE["default"]


def get_all_knowledge_texts() -> list[dict]:
    """
    Export all knowledge base entries as text documents for FAISS indexing.
    The "default" entry is excluded from the index.
    """
    documents = []
    for skill, knowledge in SKILL_KNOWLEDGE_BASE.items():
        if skill == "default":
            continue
        doc_text = (
            f"Skill: {skill}\n"
            f"Description: {knowledge['description']}\n"
            f"Learning Resources: {', '.join(knowledge['learning_resources'])}\n"
            f"Project Ideas: {', '.join(knowledge['project_ideas'])}\n"
            f"Career Paths: {', '.join(knowledge['career_paths'])}\n"
        )
        documents.append({
            "skill":    skill,
            "text":     doc_text,
            "metadata": knowledge,
        })
    return documents