"""
Script to generate 15 diverse and Python-focused resumes in resumes/ directory across PDF, DOCX, and TXT formats.
10 resumes across diverse domains (Frontend, Mobile, Java, Cloud Security, Product Management, QA Automation, Embedded, Data Analysis, UI/UX Design, DevOps/SRE).
5 resumes specifically focused on Python (Backend Microservices, GenAI/NLP, Data Engineering, MLOps, Quant Developer).
"""

import os
from docx import Document


def create_text_pdf(filepath: str, lines: list[str]) -> None:
    """Generate a clean, valid PDF containing the specified lines of text."""
    stream_lines = ['BT', '/F1 10 Tf', '14 TL', '72 750 Td']
    for idx, line in enumerate(lines):
        escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        if idx == 0:
            stream_lines.append(f'({escaped}) Tj')
        else:
            stream_lines.append(f'T* ({escaped}) Tj')
    stream_lines.append('ET')
    stream_content = '\n'.join(stream_lines).encode('latin-1', errors='replace')

    stream_obj = f'4 0 obj\n<< /Length {len(stream_content)} >>\nstream\n'.encode('latin-1') + stream_content + b'\nendstream\nendobj\n'
    
    header = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'
    obj1 = b'1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n'
    obj2 = b'2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n'
    obj3 = b'3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n'
    obj5 = b'5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n'
    
    body = header + obj1 + obj2 + obj3 + stream_obj + obj5
    offset1 = len(header)
    offset2 = offset1 + len(obj1)
    offset3 = offset2 + len(obj2)
    offset4 = offset3 + len(obj3)
    offset5 = offset4 + len(stream_obj)
    startxref = len(body)
    
    xref = f'xref\n0 6\n0000000000 65535 f \n{offset1:010d} 00000 n \n{offset2:010d} 00000 n \n{offset3:010d} 00000 n \n{offset4:010d} 00000 n \n{offset5:010d} 00000 n \ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n'.encode('latin-1')
    
    with open(filepath, 'wb') as f:
        f.write(body + xref)


def create_docx(filepath: str, title: str, sections: dict[str, list[str]]) -> None:
    """Generate a clean DOCX document with headers and bullet items."""
    doc = Document()
    doc.add_heading(title, 0)
    for heading, items in sections.items():
        doc.add_heading(heading, level=1)
        for item in items:
            doc.add_paragraph(item)
    doc.save(filepath)


def create_txt(filepath: str, text: str) -> None:
    """Generate a UTF-8 text resume file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text.strip() + '\n')


def generate_all_resumes(resumes_dir: str = "resumes") -> None:
    os.makedirs(resumes_dir, exist_ok=True)

    # =========================================================================
    # Group 1: 10 Various Resumes in Diverse Tech & Product Domains
    # =========================================================================

    # 1. Sarah Connor - Lead Frontend Engineer (DOCX)
    create_docx(
        os.path.join(resumes_dir, "sarah_connor_frontend.docx"),
        "Sarah Connor - Lead Frontend Engineer",
        {
            "Contact": ["Email: sarah.connor@example.com | Location: Austin, TX | GitHub: github.com/sarahconnor"],
            "Professional Summary": [
                "Senior Frontend Engineer with 7 years of experience building responsive, accessible web applications.",
                "Specialized in React, Next.js, TypeScript, and modern state management with Redux Toolkit and Zustand."
            ],
            "Experience": [
                "Lead Frontend Developer - PixelCraft Studios (2020 - Present):",
                "- Built design systems using TailwindCSS and Storybook adopted across 12 product teams.",
                "- Optimized Lighthouse performance scores from 65 to 98 on high-traffic e-commerce storefronts.",
                "Frontend Engineer - UI Frontiers (2017 - 2020):",
                "- Developed interactive dashboards using React and D3.js handling streaming telemetry data.",
                "- Converted legacy JavaScript codebases into strict TypeScript."
            ],
            "Skills": ["React, Next.js, TypeScript, JavaScript (ES6+), HTML5, CSS3, TailwindCSS, Webpack, Vitest, GraphQL"]
        }
    )

    # 2. Marcus Vance - Senior Mobile Developer (PDF)
    create_text_pdf(
        os.path.join(resumes_dir, "marcus_vance_mobile.pdf"),
        [
            "Marcus Vance - Senior Mobile Developer",
            "Email: marcus.vance@example.com | Location: Chicago, IL",
            "",
            "Professional Summary:",
            "Mobile software engineer with 6+ years specializing in native iOS and Android development.",
            "Deep experience with Swift, SwiftUI, Kotlin, Jetpack Compose, and cross-platform Flutter.",
            "",
            "Experience:",
            "- Senior iOS Developer at AppVenture Labs (2019 - Present)",
            "  * Spearheaded flagship iOS application rewrite in SwiftUI with 1M+ active monthly users.",
            "  * Implemented offline-first synchronization using CoreData and GraphQL subscriptions.",
            "- Android Engineer at MobileForge (2016 - 2019)",
            "  * Built multi-module Android apps using Kotlin and Coroutines adhering to Clean Architecture.",
            "",
            "Key Skills:",
            "Swift, SwiftUI, Kotlin, Jetpack Compose, Objective-C, Flutter, Xcode, Android Studio, Firebase."
        ]
    )

    # 3. Priya Patel - Enterprise Java Architect (TXT)
    create_txt(
        os.path.join(resumes_dir, "priya_patel_java.txt"),
        """Priya Patel
Enterprise Java Backend Architect
Email: priya.patel@example.com | Location: New York, NY | LinkedIn: linkedin.com/in/priyapatel-java

Summary:
Distinguished Java Engineer with 9 years of experience designing mission-critical distributed systems in fintech.
Specialized in Java 21, Spring Boot, Spring Cloud, Apache Kafka, and resilient event-driven architectures.

Experience:
Principal Java Engineer | Global Financial Services (2018 - Present)
- Designed high-frequency transactional messaging architecture processing 100k events/sec using Kafka and Spring Boot.
- Migrated legacy monolithic enterprise banking applications into decoupled microservices on OpenShift.
- Championed zero-downtime database migrations across distributed Oracle and PostgreSQL databases.

Senior Backend Developer | Nexa Systems (2014 - 2018)
- Developed secure RESTful APIs adhering to open banking standards with OAuth2 and JWT.
- Integrated Hibernate and JPA caching strategies, cutting database CPU utilization by 30%.

Technical Skills:
- Core Languages: Java 17/21, Kotlin, SQL
- Frameworks: Spring Boot, Spring Cloud, Spring Data, Hibernate, Quarkus
- Messaging & Databases: Apache Kafka, RabbitMQ, PostgreSQL, Oracle DB, Redis
- Tools: Docker, Kubernetes, Jenkins, Maven, Gradle, Splunk
"""
    )

    # 4. Elena Rostova - Cloud Security Specialist (DOCX)
    create_docx(
        os.path.join(resumes_dir, "elena_rostova_security.docx"),
        "Elena Rostova - Cloud Security & Penetration Testing Specialist",
        {
            "Contact": ["Email: elena.rostova@example.com | Location: Denver, CO | CISSP, CEH Certified"],
            "Professional Summary": [
                "Cybersecurity architect with 8 years of experience securing multi-cloud infrastructure and conducting penetration tests.",
                "Expert in DevSecOps pipelines, automated vulnerability assessments, AWS IAM hardening, and SOC 2 Type II compliance."
            ],
            "Experience": [
                "Lead Security Engineer - CyberShield Solutions (2021 - Present):",
                "- Architected automated compliance scanning covering 250+ AWS and Azure cloud accounts.",
                "- Conducted internal red team operations and vulnerability assessments against web applications.",
                "Security Analyst - DefendPoint Security (2018 - 2021):",
                "- Configured SIEM alerting with Splunk and managed incident response investigations.",
                "- Integrated SAST and DAST tooling into GitHub Actions CI/CD workflows."
            ],
            "Skills": ["AWS IAM, Azure Security, SIEM (Splunk), Wireshark, Burp Suite, Kali Linux, OWASP Top 10, Terraform, Bash"]
        }
    )

    # 5. David Kim - Senior Product Manager (PDF)
    create_text_pdf(
        os.path.join(resumes_dir, "david_kim_product_manager.pdf"),
        [
            "David Kim - Senior Technical Product Manager",
            "Email: david.kim@example.com | Location: Seattle, WA",
            "",
            "Professional Summary:",
            "Results-oriented Product Manager with 8 years guiding enterprise B2B SaaS products from discovery to scale.",
            "Proven track record increasing annual recurring revenue (ARR) and user retention through data-driven feature planning.",
            "",
            "Experience:",
            "- Senior Technical PM at SaaS Dynamics (2020 - Present)",
            "  * Led cross-functional team of 14 engineers, designers, and marketers across 3 core product initiatives.",
            "  * Increased product adoption by 45% through self-service onboarding redesign and in-app analytics.",
            "- Product Manager at InnovateLab Products (2016 - 2020)",
            "  * Managed product backlog, conducted 100+ user interviews, and drove bi-weekly sprint planning.",
            "",
            "Skills:",
            "Product Roadmapping, Agile/Scrum, JIRA, Mixpanel, Amplitude, A/B Testing, User Research, SQL."
        ]
    )

    # 6. Rachel Adams - Lead QA Automation Engineer (TXT)
    create_txt(
        os.path.join(resumes_dir, "rachel_adams_qa.txt"),
        """Rachel Adams
Lead QA Automation Engineer
Email: rachel.adams@example.com | Location: Boston, MA | GitHub: github.com/racheladams-qa

Summary:
Quality Assurance leader with 7 years of expertise establishing test automation frameworks for web, mobile, and APIs.
Champion of Shift-Left testing principles, continuous integration test suites, and performance benchmarking.

Experience:
Lead QA Automation Engineer | QualityLogic Inc (2019 - Present)
- Built enterprise-grade end-to-end automation suite with Playwright and TypeScript, reducing test execution time by 60%.
- Created regression test automation suites covering 1,200+ test cases integrated into GitLab CI.
- Mentored junior QA engineers in writing robust BDD scenarios using Cucumber and Gherkin.

Senior QA Engineer | TestWave Software (2016 - 2019)
- Automated API functional testing with RestAssured and Postman Newman CLI.
- Maintained Selenium WebDriver grid executing distributed parallel browser test suites.

Technical Skills:
- Frameworks: Playwright, Cypress, Selenium WebDriver, RestAssured, Appium, Cucumber BDD
- Languages: TypeScript, JavaScript, Java, Groovy
- CI/CD & Testing Tools: GitHub Actions, Jenkins, Postman, JMeter, TestRail, Docker
"""
    )

    # 7. Carlos Mendez - Embedded Systems Engineer (DOCX)
    create_docx(
        os.path.join(resumes_dir, "carlos_mendez_embedded.docx"),
        "Carlos Mendez - Embedded Systems & Firmware Engineer",
        {
            "Contact": ["Email: carlos.mendez@example.com | Location: San Jose, CA"],
            "Professional Summary": [
                "Embedded firmware engineer with 6 years of experience programming microcontrollers and real-time operating systems.",
                "Deep knowledge of C, C++, ARM Cortex-M, hardware peripheral protocols, and low-power IoT architectures."
            ],
            "Experience": [
                "Firmware Engineer - AutoDrive Robotics (2019 - Present):",
                "- Developed safety-critical sensor fusion firmware on ARM Cortex-M7 running FreeRTOS.",
                "- Implemented reliable serial communication over CAN, SPI, I2C, and UART interfaces.",
                "Embedded Developer - MicroTech Instruments (2015 - 2019):",
                "- Wrote low-level device drivers and board support packages (BSP) for battery-operated medical monitors.",
                "- Conducted oscilloscope and logic analyzer debugging to resolve signal integrity bottlenecks."
            ],
            "Skills": ["C, C++17, FreeRTOS, ARM Cortex-M, CAN Bus, I2C, SPI, UART, BLE, Hardware Debugging, JTAG"]
        }
    )

    # 8. Linda Wu - BI & Data Analyst (PDF)
    create_text_pdf(
        os.path.join(resumes_dir, "linda_wu_data_analyst.pdf"),
        [
            "Linda Wu - Lead Business Intelligence & Data Analyst",
            "Email: linda.wu@example.com | Location: Atlanta, GA",
            "",
            "Professional Summary:",
            "Senior Data Analyst with 7 years turning complex data into actionable operational strategies.",
            "Expertise in modern cloud data warehouses (Snowflake, BigQuery), SQL query tuning, and Tableau visualization.",
            "",
            "Experience:",
            "- Lead BI Analyst at Retail Insights Analytics (2020 - Present)",
            "  * Built automated executive dashboards in Tableau tracking $120M in omnichannel revenue.",
            "  * Formulated customer segmentation models that boosted targeted marketing conversion by 22%.",
            "- Data Analyst at Beacon Metrics (2017 - 2020)",
            "  * Modeled ETL data pipelines in Snowflake and dbt to aggregate multi-source sales records.",
            "",
            "Skills:",
            "Advanced SQL, Tableau, Power BI, Snowflake, BigQuery, dbt, Looker, Excel VBA, Statistical Analysis."
        ]
    )

    # 9. Oliver Twist - Principal UI/UX Designer (TXT)
    create_txt(
        os.path.join(resumes_dir, "oliver_twist_uiux.txt"),
        """Oliver Twist
Principal Product & UI/UX Designer
Email: oliver.twist@example.com | Location: Los Angeles, CA | Portfolio: oliverdesign.portfolio.io

Summary:
Product designer with 8 years crafting user-centered digital products across web, mobile, and desktop ecosystems.
Specialized in design systems, high-fidelity interactive prototyping, usability research, and developer handoffs.

Experience:
Principal Product Designer | Creative Aura Labs (2020 - Present)
- Architected unified multi-brand design system in Figma comprising 300+ tokenized UI components.
- Led user research workshops and contextual inquiries with 50+ enterprise clients to redesign workflow UX.
- Improved product task completion rate by 34% through iterative usability testing and information architecture refinements.

Senior UX Designer | Studio Velocity (2016 - 2020)
- Designed end-to-end user journeys, wireframes, and clickable prototypes for FinTech mobile applications.
- Collaborated closely with React Native engineering teams during sprint grooming and QA design reviews.

Design Tools & Skills:
- Design & Prototyping: Figma, FigJam, Sketch, Adobe XD, Principle, InVision
- Methods: User Journey Mapping, Wireframing, Rapid Prototyping, Usability Testing, Heuristic Evaluation
- Technical Literacy: HTML5, CSS3, CSS Grid, Design Tokens, Accessibility (WCAG 2.1 AA)
"""
    )

    # 10. Taro Yamamoto - Site Reliability & Infrastructure Engineer (DOCX)
    create_docx(
        os.path.join(resumes_dir, "taro_yamamoto_devops_go.docx"),
        "Taro Yamamoto - Site Reliability Engineer (SRE)",
        {
            "Contact": ["Email: taro.yamamoto@example.com | Location: Portland, OR"],
            "Professional Summary": [
                "Site Reliability Engineer with 7 years of experience maintaining 99.99% uptime for cloud infrastructure.",
                "Strong background in Go, Kubernetes operators, Terraform automation, Prometheus monitoring, and incident management."
            ],
            "Experience": [
                "Senior SRE - CloudNative Systems (2020 - Present):",
                "- Implemented custom Kubernetes operators in Go to automate database failovers and backups.",
                "- Designed multi-region AWS cloud foundation using Terraform with automated drift detection.",
                "DevOps Engineer - ScaleGrid Networks (2017 - 2020):",
                "- Deployed Prometheus, Alertmanager, and Grafana monitoring stacks across 40+ microservices.",
                "- Spearheaded on-call postmortems and established error budget policies with engineering teams."
            ],
            "Skills": ["Golang, Kubernetes, Docker, Helm, Terraform, AWS, Prometheus, Grafana, Linux Systems, Ansible"]
        }
    )

    # =========================================================================
    # Group 2: 5 Different Resumes Specifically Focused on Python
    # =========================================================================

    # 11. Michael Chang - Senior Python Backend Architect (DOCX)
    create_docx(
        os.path.join(resumes_dir, "michael_chang_python_backend.docx"),
        "Michael Chang - Senior Python Backend Architect",
        {
            "Contact": ["Email: michael.chang@example.com | Location: San Francisco, CA | GitHub: github.com/mchang-python"],
            "Professional Summary": [
                "Backend architect with 8 years specializing in high-throughput distributed microservices using Python.",
                "Expert in Python 3.12, FastAPI, Django REST Framework, AsyncIO, PostgreSQL, Redis, and event streaming with RabbitMQ."
            ],
            "Experience": [
                "Lead Python Backend Engineer - Apex Web Platforms (2021 - Present):",
                "- Architected asynchronous API gateway handling 30,000 requests/sec using Python, FastAPI, and uvloop.",
                "- Redesigned background batch processing pipeline with Celery and Redis, reducing queue lag by 80%.",
                "- Enforced strict Python typing with mypy and automated testing via pytest, achieving 95% test coverage.",
                "Senior Python Developer - NovaStack Systems (2017 - 2021):",
                "- Developed enterprise SaaS billing and subscription microservices in Python with Django and PostgreSQL.",
                "- Built automated database migration tooling and optimized complex SQLAlchemy queries."
            ],
            "Core Python Skills": [
                "Python 3.10/3.11/3.12, FastAPI, Django, Flask, AsyncIO, Celery, SQLAlchemy, Pydantic, pytest, Docker, Redis"
            ]
        }
    )

    # 12. Sophia Alvarez - Generative AI & NLP Research Scientist (PDF)
    create_text_pdf(
        os.path.join(resumes_dir, "sophia_alvarez_python_ai_ds.pdf"),
        [
            "Sophia Alvarez - Generative AI & NLP Research Scientist",
            "Email: sophia.alvarez@example.com | Location: Palo Alto, CA",
            "",
            "Professional Summary:",
            "AI researcher with 6+ years using Python for natural language processing and generative language models.",
            "Extensive experience fine-tuning LLMs with PyTorch, building RAG systems with LangChain, and vector embeddings.",
            "",
            "Experience:",
            "- Senior AI Scientist at Cognitive DeepLab (2021 - Present)",
            "  * Built production Python RAG pipeline with LlamaIndex, LangChain, and Qdrant vector database.",
            "  * Fine-tuned open-source LLMs using PyTorch and Hugging Face PEFT/LoRA, reducing hallucination by 40%.",
            "- NLP Engineer at TensorWave AI (2018 - 2021)",
            "  * Developed custom Python NLP pipelines for semantic search and intent classification using spaCy.",
            "  * Scaled model inference on multi-GPU clusters using Ray and Triton.",
            "",
            "Python & AI Skills:",
            "Python, PyTorch, Hugging Face, LangChain, LlamaIndex, NumPy, Pandas, Scikit-Learn, ChromaDB, FastAPI."
        ]
    )

    # 13. Dmitry Ivanov - Principal Python Data Engineer (TXT)
    create_txt(
        os.path.join(resumes_dir, "dmitry_ivanov_python_data_engineer.txt"),
        """Dmitry Ivanov
Principal Python Data Engineer
Email: dmitry.ivanov@example.com | Location: New York, NY | GitHub: github.com/divanov-data

Summary:
Senior Data Engineer with 8 years of experience constructing large-scale data lakehouse architectures using Python.
Deep expertise in PySpark, Apache Airflow, Delta Lake, Snowflake, and streaming event ingestion.

Experience:
Principal Data Engineer | BigData Stream Corp (2020 - Present)
- Engineered enterprise batch and streaming pipelines processing 10TB+ daily using Python, PySpark, and AWS EMR.
- Programmed custom Python DAGs and operators in Apache Airflow managing 500+ daily scheduled pipeline runs.
- Reduced data transformation runtime by 55% by tuning PySpark partition strategies and memory serialization.

Senior Data Pipeline Engineer | Lakehouse Analytics (2016 - 2020)
- Developed robust Python ETL scripts extracting data from REST APIs, Salesforce, and Postgres into Snowflake.
- Integrated automated data validation and schema drift detection using Great Expectations in Python.

Technical Skills:
- Primary Languages: Python, SQL, Scala
- Python Data Stack: PySpark, Pandas, Polars, Apache Airflow, dbt, Fastparquet, SQLAlchemy
- Cloud & Storage: Snowflake, Delta Lake, AWS S3, Apache Kafka, Databricks, Docker
"""
    )

    # 14. Charlotte Brown - Python MLOps Engineer (DOCX)
    create_docx(
        os.path.join(resumes_dir, "charlotte_brown_python_mlops.docx"),
        "Charlotte Brown - Python Machine Learning Operations (MLOps) Engineer",
        {
            "Contact": ["Email: charlotte.brown@example.com | Location: Austin, TX | GitHub: github.com/cbrown-mlops"],
            "Professional Summary": [
                "MLOps engineer with 6 years bridging data science and production operations using Python cloud tooling.",
                "Specialized in automated ML pipelines, experiment tracking with MLflow, continuous model deployment, and monitoring."
            ],
            "Experience": [
                "Senior MLOps Engineer - NeuralDeploy Solutions (2021 - Present):",
                "- Created end-to-end Python model delivery pipelines on Kubeflow and AWS SageMaker.",
                "- Implemented automated model registry and artifact tracking with MLflow and DVC in Python.",
                "- Built low-latency model inference microservices in Python with FastAPI and ONNX Runtime.",
                "Machine Learning Engineer - ScaledML Technologies (2018 - 2021):",
                "- Automated model training workflows using Python, Ray, and Celery distributed task queues.",
                "- Established automated model drift detection and performance monitoring dashboards."
            ],
            "Python & MLOps Skills": [
                "Python, MLflow, Kubeflow, Ray, FastAPI, Docker, Kubernetes, AWS SageMaker, ONNX, DVC, Prometheus"
            ]
        }
    )

    # 15. Liam Wilson - Python Quantitative Developer (PDF)
    create_text_pdf(
        os.path.join(resumes_dir, "liam_wilson_python_quant.pdf"),
        [
            "Liam Wilson - Quantitative Developer & Python Financial Modeler",
            "Email: liam.wilson@example.com | Location: Chicago, IL",
            "",
            "Professional Summary:",
            "Quantitative finance developer with 7 years building high-speed mathematical modeling engines in Python.",
            "Expertise in algorithmic trading systems, stochastic calculus, Monte Carlo simulations, and numerical Python libraries.",
            "",
            "Experience:",
            "- Senior Quantitative Developer at Quantum Capital Partners (2019 - Present)",
            "  * Implemented parallel Monte Carlo risk engine in Python with NumPy and Numba running 10x faster.",
            "  * Designed automated backtesting framework in Python processing multi-asset historical tick data.",
            "- Quantitative Research Associate at AlphaEdge Analytics (2015 - 2019)",
            "  * Formulated statistical arbitrage and mean-reversion trading algorithms using Python and Pandas.",
            "  * Integrated C extensions with Cython to accelerate critical pricing loops.",
            "",
            "Core Technologies:",
            "Python, NumPy, SciPy, Pandas, Numba, Cython, Polars, Statsmodels, Jupyter, C++, Linux."
        ]
    )

    print("Successfully generated all 15 resumes in resumes/ directory!")


if __name__ == "__main__":
    generate_all_resumes()
