# Ghana Parliamentary Data Analysis Platform (OpenParlGH)

## Project Overview

This project creates a structured database and analytical platform for parliamentary debates in Ghana. It addresses the critical challenge of unstructured parliamentary data by providing researchers, journalists, civic society organizations, and citizens with accessible tools to search, analyze, and visualize legislative information.

## Project Goals

- **Data Accessibility**: Transform unstructured Hansard data into a well-organized, machine-readable database
- **Public Engagement**: Develop an interactive, user-friendly portal for accessing parliamentary information
- **Advanced Analytics**: Provide specialized analytical tools including sentiment analysis and topic modeling
- **Transparency & Accountability**: Enable evidence-based research and informed public discourse on governance

## Key Features

### 1. Home Dashboard
- Interactive analytics dashboard displaying key parliamentary metrics
- Number of debates analyzed
- Active members of parliament statistics
- Most frequently discussed topics
- Average sentiment indices

### 2. Debates Explorer
- Sort and filter debates by time, topic, or speakers
- Observe sentiment changes throughout debates
- Download debate fragments
- Full-text search capabilities

### 3. Speaker Analytics
- Word clouds showing frequently used terms by speakers
- Contribution frequency visualizations
- Sentiment trend analysis
- Topic coverage by MP

### 4. Advanced Analytics
- **Sentiment Analysis**: Track emotional tone and sentiment changes over time
- **Topic Modeling**: Identify and track major legislative themes
- **Performance Metrics**: Analyze MP contributions and engagement patterns
- **Visualization Tools**: Interactive charts, heat maps, pie charts

## Technology Stack

### Backend
- **Framework**: Django 5.0
- **Database**: PostgreSQL 16
- **Language**: Python 3.11

### Frontend
- **Library**: React 18
- **Language**: JavaScript (ES6+)

### NLP & Analytics
- **spaCy**: Industrial-strength NLP processing
- **NLTK**: Natural Language Toolkit
- **Scikit-learn**: Machine learning algorithms

### DevOps
- **Version Control**: Git & GitHub
- **Server Environment**: ASGI/WSGI compatible

## Installation & Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 16+
- Node.js (for frontend)
- Virtual environment (venv)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure database**
   - Update `backend/settings.py` with PostgreSQL credentials
   - Run migrations:
     ```bash
     python manage.py migrate
     ```

5. **Download Hansard Data**
   ```bash
   python manage.py download_hansards
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

## Project Structure

```
backend/
├── app/                          # Main Django application
│   ├── migrations/               # Database migrations
│   ├── management/               # Custom management commands
│   │   └── commands/
│   │       └── download_hansards.py
│   ├── scheduler/                # Background job scheduler
│   ├── utils/                    # Utility modules
│   │   ├── hansard_pipeline.py   # Data processing pipeline
│   │   ├── hansards_downloader.py # Download utilities
│   │   ├── summarizer.py         # Text summarization
│   │   └── pipeline.py           # Data flow orchestration
│   ├── models.py                 # Database models
│   ├── views.py                  # View controllers
│   ├── urls.py                   # URL routing
│   ├── forms.py                  # Django forms
│   └── templates/                # HTML templates
├── backend/                      # Django settings
│   ├── settings.py               # Configuration
│   ├── urls.py                   # Main URL configuration
│   └── wsgi.py                   # WSGI application
├── media/                        # User-uploaded files
├── db.sqlite3                    # Development database
└── manage.py                     # Django management script
```

## Database Models

### Core Models
- **HansardFile**: Parliamentary debate records
- **Session**: Parliamentary sessions/dates
- **Speaker**: MPs and parliament members
- **DebateSegment**: Individual debate contributions
- **Summary**: Automated debate summaries
- **Topic**: Topic classifications
- **ParliamentaryLeadership**: Leadership positions and roles

## Key Utilities

### Hansard Pipeline (`utils/hansard_pipeline.py`)
Processes raw Hansard data through:
- Data extraction and cleaning
- Speaker attribution
- Topic classification
- Sentiment analysis

### Summarizer (`utils/summarizer.py`)
- Automatic text summarization
- Action item extraction
- Timeline generation

### Progress Tracking (`utils/progress.py`)
- Monitor long-running operations
- Batch processing status

## System Evaluation

### Performance Metrics
- **Functional Testing**: 92% success rate
- **User Satisfaction**: 80% of users found the system user-friendly
- **Data Accuracy**: Outperformed comparable systems (90%+ accuracy)
- **Server Performance**: Handles large datasets on mid-level servers (8GB RAM, 4-core CPU)

### Target User Groups
- **Researchers**: Access to structured datasets for longitudinal studies
- **Journalists**: Investigative reporting resources
- **Civic Society**: Governance monitoring and advocacy
- **Citizens**: Transparency and accountability tools

## Limitations

- Incomplete digitization of historical records
- Sentiment analysis may not detect sarcasm
- Limited handling of non-English expressions
- Performance dependent on hosting environment

## Future Enhancements

- Expanded language support
- Real-time debate processing
- Mobile application development
- Advanced predictive analytics
- Integration with other government data sources

## API Documentation

The platform provides RESTful APIs for:
- Debate search and retrieval
- Speaker analytics queries
- Sentiment and topic data
- Custom report generation

(Detailed API documentation available in `/docs/api/`)

## Contributing

### Development Workflow
1. Create feature branch
2. Make changes following Python/Django conventions
3. Add tests for new functionality
4. Submit pull request with description

### Code Standards
- Follow PEP 8 style guidelines
- Write meaningful commit messages
- Include docstrings for functions and classes

## Testing

Run tests with:
```bash
python manage.py test
```

## Project Team

### Developers
- **Owusu Fosu Clifford** (ID: UEB3204022)
- **Ampaabeng Degraft** (ID: UEB3211922)
- **Antwi Osei Emmanuel** (ID: UEB3212922)

### Supervision
- **Professor Peter Appiahene** - Project Supervisor

## License

This project is developed for the Ghana Parliament and is subject to the applicable Ghana Government Data policies.

## Support & Documentation

- **Project Report**: See `SETUP_SUMMARIZATION.md` and `SUMMARIZATION_FEATURE.md`
- **API Docs**: `/docs/api/`
- **Architecture**: See project report for detailed system architecture

## Contact

For questions or support, please contact the project team or submit issues through the GitHub repository.

---

**Status**: Active Development  
**Last Updated**: August 2026  
**Repository**: [OpenParlGH - PARL-GH](https://github.com/OpenParlGH/PARL-GH)
