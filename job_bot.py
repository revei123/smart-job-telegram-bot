import logging
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "# BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
DB_PATH = "jobs.db"
ADMIN_USERS = []  # Добавьте ваш user_id через @userinfobot

# Состояния для ConversationHandler
ROLE, LEVEL, FORMAT, LOCATION, SALARY, CV_UPLOAD = range(6)

class DatabaseManager:
    def __init__(self, db_path="jobs.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                role TEXT,
                level TEXT,
                work_format TEXT,
                location TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                currency TEXT,
                cv_text TEXT,
                cv_analysis TEXT,
                search_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                consent_given BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Таблица вакансий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                currency TEXT,
                location TEXT,
                work_format TEXT,
                description_short TEXT,
                requirements TEXT,
                apply_url TEXT,
                contacts TEXT,
                tags TEXT,
                industry TEXT,
                role TEXT,
                level TEXT,
                source TEXT,
                relevance_score REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица подписок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMP,
                free_applications INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица действий пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                vacancy_id INTEGER,
                action TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица платежей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id TEXT,
                amount REAL,
                currency TEXT DEFAULT 'USD',
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Добавляем тестовые вакансии
        self.add_sample_vacancies()
    
    def add_sample_vacancies(self):
        """Добавляем примеры вакансий в базу"""
        vacancies = [
            {
                'title': 'Python Backend Developer',
                'company': 'Tech Innovations Inc.',
                'salary_min': 3000,
                'salary_max': 5000,
                'currency': 'USD',
                'location': 'Remote / Moscow',
                'work_format': 'remote',
                'description_short': 'We are looking for an experienced backend engineer with Django or FastAPI. You will build and maintain microservices, improve performance and optimize databases.',
                'requirements': 'Python, SQL, Docker, production experience 3+ years',
                'apply_url': 'https://example.com/apply/python-dev',
                'contacts': 'hr@techinnovations.com',
                'tags': 'python,backend,django,postgresql',
                'industry': 'FinTech',
                'role': 'backend',
                'level': 'middle',
                'source': 'sample'
            },
            {
                'title': 'Frontend React Developer',
                'company': 'Web Solutions LLC',
                'salary_min': 2500,
                'salary_max': 4000,
                'currency': 'USD',
                'location': 'Remote',
                'work_format': 'remote',
                'description_short': 'Join our frontend team to build amazing user interfaces with React.',
                'requirements': 'JavaScript, React, TypeScript, CSS, 2+ years experience',
                'apply_url': 'https://example.com/apply/react-dev',
                'contacts': 'jobs@websolutions.com',
                'tags': 'react,frontend,javascript,typescript',
                'industry': 'SaaS',
                'role': 'frontend',
                'level': 'middle',
                'source': 'sample'
            },
            {
                'title': 'DevOps Engineer',
                'company': 'Cloud Systems',
                'salary_min': 4000,
                'salary_max': 6000,
                'currency': 'USD',
                'location': 'Remote / Berlin',
                'work_format': 'remote',
                'description_short': 'We need a DevOps engineer to manage our cloud infrastructure.',
                'requirements': 'AWS, Docker, Kubernetes, CI/CD, Terraform, 4+ years experience',
                'apply_url': 'https://example.com/apply/devops',
                'contacts': 'careers@cloudsystems.com',
                'tags': 'devops,aws,docker,kubernetes',
                'industry': 'Cloud',
                'role': 'devops',
                'level': 'senior',
                'source': 'sample'
            },
            {
                'title': 'UI/UX Designer',
                'company': 'Creative Agency',
                'salary_min': 2000,
                'salary_max': 3500,
                'currency': 'USD',
                'location': 'Remote / Warsaw',
                'work_format': 'remote',
                'description_short': 'Looking for a talented designer to create beautiful user interfaces.',
                'requirements': 'Figma, Adobe Creative Suite, UI/UX design, 2+ years experience',
                'apply_url': 'https://example.com/apply/designer',
                'contacts': 'design@creativeagency.com',
                'tags': 'design,ui,ux,figma',
                'industry': 'Design',
                'role': 'design',
                'level': 'middle',
                'source': 'sample'
            },
            {
                'title': 'Data Scientist',
                'company': 'AI Research Lab',
                'salary_min': 4500,
                'salary_max': 7000,
                'currency': 'USD',
                'location': 'Remote',
                'work_format': 'remote',
                'description_short': 'Join our AI team to work on cutting-edge machine learning projects.',
                'requirements': 'Python, Machine Learning, TensorFlow, SQL, 3+ years experience',
                'apply_url': 'https://example.com/apply/data-scientist',
                'contacts': 'research@ailab.com',
                'tags': 'data-science,python,machine-learning,ai',
                'industry': 'AI',
                'role': 'ai',
                'level': 'senior',
                'source': 'sample'
            },
            {
                'title': 'Product Manager',
                'company': 'SaaS Startup',
                'salary_min': 4000,
                'salary_max': 6500,
                'currency': 'USD',
                'location': 'Remote / London',
                'work_format': 'remote',
                'description_short': 'We are looking for a Product Manager to drive our product strategy.',
                'requirements': 'Product management, Agile, User research, 4+ years experience',
                'apply_url': 'https://example.com/apply/pm',
                'contacts': 'products@saasstartup.com',
                'tags': 'product,management,agile',
                'industry': 'SaaS',
                'role': 'product',
                'level': 'senior',
                'source': 'sample'
            },
            {
                'title': 'Full Stack Developer',
                'company': 'Digital Agency',
                'salary_min': 3500,
                'salary_max': 5500,
                'currency': 'USD',
                'location': 'Remote',
                'work_format': 'remote',
                'description_short': 'Looking for a full stack developer to work on diverse web projects.',
                'requirements': 'JavaScript, React, Node.js, MongoDB, 3+ years experience',
                'apply_url': 'https://example.com/apply/fullstack',
                'contacts': 'dev@digitalagency.com',
                'tags': 'fullstack,react,node,mongodb',
                'industry': 'Web Development',
                'role': 'fullstack',
                'level': 'middle',
                'source': 'sample'
            }
        ]
        
        for vacancy in vacancies:
            self.save_vacancy(vacancy)
    
    def save_user(self, user_data):
        """Сохраняет пользователя в базу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, role, level, work_format, 
             location, salary_min, salary_max, currency, cv_text, cv_analysis, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_data['user_id'],
            user_data.get('username'),
            user_data.get('first_name'),
            user_data.get('last_name'),
            user_data.get('role'),
            user_data.get('level'),
            user_data.get('work_format'),
            user_data.get('location'),
            user_data.get('salary_min'),
            user_data.get('salary_max'),
            user_data.get('currency'),
            user_data.get('cv_text'),
            json.dumps(user_data.get('cv_analysis', {})),
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    def get_user(self, user_id):
        """Получает пользователя по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        columns = [description[0] for description in cursor.description]
        user = dict(zip(columns, row))
        
        if user.get('cv_analysis'):
            try:
                user['cv_analysis'] = json.loads(user['cv_analysis'])
            except:
                user['cv_analysis'] = {}
        
        conn.close()
        return user
    
    def save_vacancy(self, vacancy_data):
        """Сохраняет вакансию в базу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO vacancies 
            (title, company, salary_min, salary_max, currency, location, work_format,
             description_short, requirements, apply_url, contacts, tags, industry, role, level, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vacancy_data['title'],
            vacancy_data.get('company'),
            vacancy_data.get('salary_min'),
            vacancy_data.get('salary_max'),
            vacancy_data.get('currency', 'USD'),
            vacancy_data.get('location', 'Remote'),
            vacancy_data.get('work_format', 'remote'),
            vacancy_data.get('description_short', ''),
            vacancy_data.get('requirements', ''),
            vacancy_data.get('apply_url', ''),
            vacancy_data.get('contacts', ''),
            vacancy_data.get('tags', ''),
            vacancy_data.get('industry', ''),
            vacancy_data.get('role', ''),
            vacancy_data.get('level', ''),
            vacancy_data.get('source', 'manual')
        ))
        
        conn.commit()
        conn.close()
        return True
    
    def get_vacancies(self, limit=5, offset=0, filters=None):
        """Получает вакансии из базы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM vacancies WHERE 1=1"
        params = []
        
        if filters:
            if filters.get('role'):
                query += " AND role = ?"
                params.append(filters['role'])
            if filters.get('level'):
                query += " AND level = ?"
                params.append(filters['level'])
            if filters.get('work_format'):
                query += " AND work_format = ?"
                params.append(filters['work_format'])
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        vacancies = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return vacancies
    
    def get_vacancy(self, vacancy_id):
        """Получает вакансию по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM vacancies WHERE id = ?', (vacancy_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        columns = [description[0] for description in cursor.description]
        vacancy = dict(zip(columns, row))
        
        conn.close()
        return vacancy
    
    def save_user_action(self, user_id, vacancy_id, action):
        """Сохраняет действие пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO user_actions (user_id, vacancy_id, action)
            VALUES (?, ?, ?)
        ''', (user_id, vacancy_id, action))
        
        conn.commit()
        conn.close()
    
    def get_user_actions(self, user_id, action_type=None):
        """Получает действия пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if action_type:
            cursor.execute('SELECT vacancy_id FROM user_actions WHERE user_id = ? AND action = ?', (user_id, action_type))
        else:
            cursor.execute('SELECT vacancy_id FROM user_actions WHERE user_id = ?', (user_id,))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_subscription(self, user_id):
        """Получает информацию о подписке"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        
        if not row:
            cursor.execute('INSERT INTO subscriptions (user_id, free_applications) VALUES (?, ?)', (user_id, 10))
            conn.commit()
            cursor.execute('SELECT * FROM subscriptions WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
        
        columns = [description[0] for description in cursor.description]
        subscription = dict(zip(columns, row))
        conn.close()
        
        return subscription
    
    def update_subscription(self, user_id, updates):
        """Обновляет подписку пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values())
        values.append(user_id)
        
        cursor.execute(f'UPDATE subscriptions SET {set_clause} WHERE user_id = ?', values)
        conn.commit()
        conn.close()
    
    def get_stats(self):
        """Получает статистику бота"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute('SELECT COUNT(*) FROM users')
        stats['users_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM vacancies')
        stats['vacancies_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_premium = 1')
        stats['premium_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_actions WHERE action = "applied"')
        stats['applications_count'] = cursor.fetchone()[0]
        
        conn.close()
        return stats

class SmartJobBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.db = DatabaseManager(DB_PATH)
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("profile", self.profile))
        self.application.add_handler(CommandHandler("feed", self.feed))
        self.application.add_handler(CommandHandler("saved", self.saved))
        self.application.add_handler(CommandHandler("subscription", self.subscription))
        self.application.add_handler(CommandHandler("tools", self.tools))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("admin", self.admin))
        
        # Обработчики callback запросов
        self.application.add_handler(CallbackQueryHandler(self.handle_callback, pattern="^.*$"))
        
        # Обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        # Сохраняем базовую информацию о пользователе
        user_data = {
            'user_id': user_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }
        self.db.save_user(user_data)
        
        # Проверяем, есть ли уже профиль
        existing_user = self.db.get_user(user_id)
        
        if existing_user and existing_user.get('role'):
            # Пользователь уже прошел онбординг
            await self.show_main_menu(update, f"👋 Добро пожаловать назад, {user.first_name}!")
        else:
            # Начинаем онбординг
            await self.start_onboarding(update)
    
    async def start_onboarding(self, update: Update):
        """Начинает процесс онбординга"""
        welcome_text = """
🚀 **Smart Job Bot** - ваш персональный помощник в поиске работы!

Я помогу:
• Найти релевантные вакансии из 20+ источников
• Анализировать ваше резюме и улучшать его
• Подготовиться к собеседованиям
• Автоматически отслеживать новые вакансии

Давайте настроим ваш профиль!
        """
        
        # Выбор роли
        roles_keyboard = [
            [
                InlineKeyboardButton("Engineering", callback_data="role_engineering"),
                InlineKeyboardButton("Product", callback_data="role_product"),
            ],
            [
                InlineKeyboardButton("AI/ML", callback_data="role_ai"),
                InlineKeyboardButton("Design", callback_data="role_design"),
            ],
            [
                InlineKeyboardButton("Marketing", callback_data="role_marketing"),
                InlineKeyboardButton("Sales", callback_data="role_sales"),
            ],
            [
                InlineKeyboardButton("Content", callback_data="role_content"),
                InlineKeyboardButton("Support", callback_data="role_support"),
            ]
        ]
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(roles_keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback запросов"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if data.startswith('role_'):
            await self.handle_role_selection(query, context)
        elif data.startswith('level_'):
            await self.handle_level_selection(query, context)
        elif data.startswith('format_'):
            await self.handle_format_selection(query, context)
        elif data == 'location_remote':
            await self.handle_location_remote(query, context)
        elif data == 'consent_yes':
            await self.handle_consent_yes(query)
        elif data == 'consent_no':
            await self.handle_consent_no(query)
        elif data.startswith('apply_'):
            await self.handle_apply(query, context)
        elif data.startswith('save_'):
            await self.handle_save(query, context)
        elif data.startswith('hide_'):
            await self.handle_hide(query, context)
        elif data == 'main_menu':
            await self.show_main_menu_from_query(query)
        elif data == 'setup_profile':
            await self.start_onboarding_from_query(query)
        elif data == 'find_jobs':
            await self.show_feed_from_query(query)
        elif data == 'premium_info':
            await self.show_premium_info(query)
        elif data == 'buy_premium':
            await self.handle_buy_premium(query)
        elif data.startswith('page_'):
            await self.handle_pagination(query, context)
        elif data == 'admin_stats':
            await self.show_admin_stats(query)
        elif data == 'admin_broadcast':
            await self.start_admin_broadcast(query, context)
        elif data == 'admin_add_vacancy':
            await self.start_admin_add_vacancy(query, context)
    
    async def handle_role_selection(self, query, context):
        """Обработка выбора роли"""
        role = query.data.replace('role_', '')
        context.user_data['role'] = role
        
        # Выбор уровня
        level_keyboard = [
            [InlineKeyboardButton("Junior", callback_data="level_junior")],
            [InlineKeyboardButton("Middle", callback_data="level_middle")],
            [InlineKeyboardButton("Senior", callback_data="level_senior")],
            [InlineKeyboardButton("Lead", callback_data="level_lead")]
        ]
        
        await query.edit_message_text(
            "🎯 Отлично! Теперь выберите ваш уровень:",
            reply_markup=InlineKeyboardMarkup(level_keyboard)
        )
    
    async def handle_level_selection(self, query, context):
        """Обработка выбора уровня"""
        level = query.data.replace('level_', '')
        context.user_data['level'] = level
        
        # Выбор формата работы
        format_keyboard = [
            [InlineKeyboardButton("Remote", callback_data="format_remote")],
            [InlineKeyboardButton("Hybrid", callback_data="format_hybrid")],
            [InlineKeyboardButton("Office", callback_data="format_office")],
            [InlineKeyboardButton("Contract", callback_data="format_contract")]
        ]
        
        await query.edit_message_text(
            "📍 Выберите предпочитаемый формат работы:",
            reply_markup=InlineKeyboardMarkup(format_keyboard)
        )
    
    async def handle_format_selection(self, query, context):
        """Обработка выбора формата работы"""
        work_format = query.data.replace('format_', '')
        context.user_data['work_format'] = work_format
        
        # Выбор локации
        location_keyboard = [
            [InlineKeyboardButton("Remote (любая локация)", callback_data="location_remote")],
        ]
        
        await query.edit_message_text(
            "🌍 Выберите предпочитаемую локацию:",
            reply_markup=InlineKeyboardMarkup(location_keyboard)
        )
    
    async def handle_location_remote(self, query, context):
        """Обработка выбора удаленной работы"""
        context.user_data['location'] = 'Remote'
        
        await query.edit_message_text(
            "💰 Укажите зарплатные ожидания (опционально):\n\n"
            "Формат: 3000-5000 USD\n"
            "Или отправьте '-' чтобы пропустить"
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        text = update.message.text
        user_id = update.effective_user.id
        
        # Если пользователь в процессе настройки профиля
        if 'role' in context.user_data and 'salary_min' not in context.user_data:
            if text != '-':
                # Парсим зарплату
                try:
                    if '-' in text and 'USD' in text:
                        amounts = text.split('USD')[0].strip().split('-')
                        salary_min = int(amounts[0].strip())
                        salary_max = int(amounts[1].strip())
                        context.user_data['salary_min'] = salary_min
                        context.user_data['salary_max'] = salary_max
                        context.user_data['currency'] = 'USD'
                    
                    await update.message.reply_text(
                        "📄 Теперь загрузите ваше резюме (CV) файлом (PDF, DOC, DOCX)\n\n"
                        "Или отправьте текст резюме сообщением"
                    )
                except:
                    await update.message.reply_text(
                        "❌ Неверный формат зарплаты. Используйте: 3000-5000 USD\n"
                        "Или отправьте '-' чтобы пропустить"
                    )
            else:
                context.user_data['salary_min'] = None
                context.user_data['salary_max'] = None
                await update.message.reply_text(
                    "📄 Загрузите ваше резюме (CV) файлом или отправьте текст резюме"
                )
        
        # Если пользователь отправил текст резюме
        elif 'role' in context.user_data and 'cv_text' not in context.user_data:
            context.user_data['cv_text'] = text
            
            # Сохраняем профиль
            user_data = {
                'user_id': user_id,
                'username': update.effective_user.username,
                'first_name': update.effective_user.first_name,
                'last_name': update.effective_user.last_name,
                'role': context.user_data.get('role'),
                'level': context.user_data.get('level'),
                'work_format': context.user_data.get('work_format'),
                'location': context.user_data.get('location'),
                'salary_min': context.user_data.get('salary_min'),
                'salary_max': context.user_data.get('salary_max'),
                'currency': context.user_data.get('currency'),
                'cv_text': text,
                'cv_analysis': {'skills': [], 'experience': 'not_analyzed'}
            }
            
            self.db.save_user(user_data)
            
            # Запрашиваем согласие
            consent_keyboard = [
                [InlineKeyboardButton("✅ Согласен", callback_data="consent_yes")],
                [InlineKeyboardButton("❌ Не согласен", callback_data="consent_no")]
            ]
            
            await update.message.reply_text(
                "📝 **Согласие на обработку персональных данных**\n\n"
                "Для работы сервиса нам необходимо обрабатывать ваши персональные данные. "
                "Мы гарантируем конфиденциальность и используем данные только для подбора вакансий.\n\n"
                "Вы согласны на обработку персональных данных?",
                reply_markup=InlineKeyboardMarkup(consent_keyboard),
                parse_mode='Markdown'
            )
        
        # Обработка админской рассылки
        elif context.user_data.get('admin_action') == 'broadcast':
            if user_id not in ADMIN_USERS:
                await update.message.reply_text("❌ Нет доступа")
                return
            
            # Получаем всех пользователей
            all_users = self.get_all_users()
            success_count = 0
            
            for user_id in all_users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode='Markdown'
                    )
                    success_count += 1
                except:
                    continue
            
            await update.message.reply_text(f"✅ Рассылка завершена! Отправлено: {success_count} пользователям")
            context.user_data['admin_action'] = None
        
        # Обработка добавления вакансии админом
        elif context.user_data.get('admin_action') == 'add_vacancy':
            if user_id not in ADMIN_USERS:
                await update.message.reply_text("❌ Нет доступа")
                return
            
            try:
                # Парсим вакансию из текста
                vacancy = self.parse_vacancy_from_text(text)
                if vacancy:
                    self.db.save_vacancy(vacancy)
                    await update.message.reply_text("✅ Вакансия успешно добавлена!")
                else:
                    await update.message.reply_text("❌ Ошибка при разборе вакансии")
            except Exception as e:
                await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            
            context.user_data['admin_action'] = None
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик документов (резюме)"""
        if 'role' in context.user_data and 'cv_text' not in context.user_data:
            document = update.message.document
            file_name = document.file_name
            
            if file_name and file_name.endswith(('.pdf', '.doc', '.docx')):
                # В реальном приложении здесь был бы код для скачивания и анализа файла
                context.user_data['cv_text'] = f"Файл резюме: {file_name}"
                
                user_id = update.effective_user.id
                user_data = {
                    'user_id': user_id,
                    'username': update.effective_user.username,
                    'first_name': update.effective_user.first_name,
                    'last_name': update.effective_user.last_name,
                    'role': context.user_data.get('role'),
                    'level': context.user_data.get('level'),
                    'work_format': context.user_data.get('work_format'),
                    'location': context.user_data.get('location'),
                    'salary_min': context.user_data.get('salary_min'),
                    'salary_max': context.user_data.get('salary_max'),
                    'currency': context.user_data.get('currency'),
                    'cv_text': f"Файл резюме: {file_name}",
                    'cv_analysis': {'skills': [], 'experience': 'not_analyzed'}
                }
                
                self.db.save_user(user_data)
                
                # Запрашиваем согласие
                consent_keyboard = [
                    [InlineKeyboardButton("✅ Согласен", callback_data="consent_yes")],
                    [InlineKeyboardButton("❌ Не согласен", callback_data="consent_no")]
                ]
                
                await update.message.reply_text(
                    "📝 **Согласие на обработку персональных данных**\n\n"
                    "Для работы сервиса нам необходимо обрабатывать ваши персональные данные. "
                    "Мы гарантируем конфиденциальность и используем данные только для подбора вакансий.\n\n"
                    "Вы согласны на обработку персональных данных?",
                    reply_markup=InlineKeyboardMarkup(consent_keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ Пожалуйста, загрузите резюме в формате PDF, DOC или DOCX"
                )
    
    async def handle_consent_yes(self, query):
        """Обработка согласия на обработку данных"""
        user_id = query.from_user.id
        
        # Обновляем статус согласия в базе
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET consent_given = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        await self.show_main_menu_from_query(query, "🎉 Профиль успешно создан! Теперь вы можете искать вакансии.")
    
    async def handle_consent_no(self, query):
        """Обработка отказа от обработки данных"""
        await query.edit_message_text(
            "❌ Для работы бота необходимо согласие на обработку данных. "
            "Если передумаете - используйте /start снова."
        )
    
    async def show_main_menu(self, update, text):
        """Показывает главное меню"""
        keyboard = [
            [InlineKeyboardButton("🎯 Профиль", callback_data="setup_profile")],
            [InlineKeyboardButton("🔍 Лента вакансий", callback_data="find_jobs")],
            [InlineKeyboardButton("⭐ Сохраненные", callback_data="saved_list")],
            [InlineKeyboardButton("💎 Подписка", callback_data="premium_info")],
            [InlineKeyboardButton("🛠 Инструменты", callback_data="tools_menu")],
            [InlineKeyboardButton("📖 Помощь", callback_data="help_menu")],
        ]
        
        await update.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_main_menu_from_query(self, query, text="🏠 **Главное меню**\n\nВыберите раздел:"):
        """Показывает главное меню из callback query"""
        keyboard = [
            [InlineKeyboardButton("🎯 Профиль", callback_data="setup_profile")],
            [InlineKeyboardButton("🔍 Лента вакансий", callback_data="find_jobs")],
            [InlineKeyboardButton("⭐ Сохраненные", callback_data="saved_list")],
            [InlineKeyboardButton("💎 Подписка", callback_data="premium_info")],
            [InlineKeyboardButton("🛠 Инструменты", callback_data="tools_menu")],
            [InlineKeyboardButton("📖 Помощь", callback_data="help_menu")],
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def start_onboarding_from_query(self, query):
        """Начинает онбординг из callback query"""
        roles_keyboard = [
            [
                InlineKeyboardButton("Engineering", callback_data="role_engineering"),
                InlineKeyboardButton("Product", callback_data="role_product"),
            ],
            [
                InlineKeyboardButton("AI/ML", callback_data="role_ai"),
                InlineKeyboardButton("Design", callback_data="role_design"),
            ],
            [
                InlineKeyboardButton("Marketing", callback_data="role_marketing"),
                InlineKeyboardButton("Sales", callback_data="role_sales"),
            ]
        ]
        
        await query.edit_message_text(
            "🎯 **Настройка профиля**\n\nВыберите вашу роль:",
            reply_markup=InlineKeyboardMarkup(roles_keyboard),
            parse_mode='Markdown'
        )
    
    async def profile(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile - показывает профиль пользователя"""
        user_id = update.effective_user.id
        user = self.db.get_user(user_id)
        
        if not user or not user.get('role'):
            await update.message.reply_text(
                "Профиль не настроен. Используйте /start для настройки."
            )
            return
        
        subscription = self.db.get_subscription(user_id)
        
        profile_text = f"""
👤 **Ваш профиль:**

🎯 **Роль:** {user.get('role', 'Не указано')}
📊 **Уровень:** {user.get('level', 'Не указано')}
📍 **Формат:** {user.get('work_format', 'Не указано')}
🌍 **Локация:** {user.get('location', 'Не указано')}
💰 **Зарплата:** {f"{user.get('salary_min', '')}-{user.get('salary_max', '')} {user.get('currency', '')}" if user.get('salary_min') else "Не указано"}
        
🔍 **Статус поиска:** {'Активен ✅' if user.get('search_active', True) else 'На паузе ⏸️'}
💎 **Подписка:** {'Premium 🚀' if subscription['is_premium'] else 'Free'}
📨 **Осталось откликов:** {subscription['free_applications'] if not subscription['is_premium'] else '∞'}
        """
        
        keyboard = [
            [InlineKeyboardButton("✏️ Изменить профиль", callback_data="setup_profile")],
            [InlineKeyboardButton("📄 Обновить резюме", callback_data="update_cv")],
            [InlineKeyboardButton("⚙️ Настроить фильтры", callback_data="setup_filters")],
            [InlineKeyboardButton("⏸️ Пауза поиска" if user.get('search_active') else "▶️ Возобновить поиск", 
                                callback_data="toggle_search")],
            [InlineKeyboardButton("💎 Подписка", callback_data="premium_info")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def feed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /feed - показывает ленту вакансий"""
        await self.show_feed(update.message, page=0)
    
    async def show_feed(self, message, page=0):
        """Показывает ленту вакансий"""
        user_id = message.from_user.id
        user = self.db.get_user(user_id)
        
        if not user or not user.get('role'):
            await message.reply_text(
                "Профиль не настроен. Используйте /start для настройки."
            )
            return
        
        # Получаем вакансии с фильтрами по профилю пользователя
        filters = {
            'role': user.get('role'),
            'level': user.get('level'),
            'work_format': user.get('work_format')
        }
        
        vacancies = self.db.get_vacancies(limit=5, offset=page*5, filters=filters)
        
        if not vacancies:
            await message.reply_text(
                "😔 Пока нет подходящих вакансий. Попробуйте позже или настройте фильтры в профиле."
            )
            return
        
        for vacancy in vacancies:
            await self.send_vacancy_message(message, vacancy, user_id)
        
        # Пагинация
        pagination_keyboard = []
        if page > 0:
            pagination_keyboard.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        
        if len(vacancies) == 5:
            pagination_keyboard.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
        
        if pagination_keyboard:
            await message.reply_text(
                "Навигация:",
                reply_markup=InlineKeyboardMarkup([pagination_keyboard])
            )
    
    async def show_feed_from_query(self, query):
        """Показывает ленту из callback query"""
        await self.show_feed(query.message, page=0)
    
    async def send_vacancy_message(self, message, vacancy, user_id):
        """Отправляет сообщение с вакансией"""
        salary_text = ""
        if vacancy.get('salary_min') and vacancy.get('salary_max'):
            salary_text = f"💵 **Salary:** {vacancy['salary_min']} - {vacancy['salary_max']} {vacancy.get('currency', 'USD')}\n"
        
        # Проверяем подписку для показа компании
        subscription = self.db.get_subscription(user_id)
        company_text = f"🏢 **Company:** {vacancy['company']}" if subscription['is_premium'] else "🏢 **Company:** [Premium only]"
        
        vacancy_text = f"""
🚀 **{vacancy['title']}**

{company_text}
{salary_text}📍 **Location:** {vacancy['location']} | {vacancy.get('work_format', 'Remote')}

📝 **Description:** {vacancy.get('description_short', '')}

🔧 **Requirements:** {vacancy.get('requirements', '')}
        """
        
        keyboard = self.get_vacancy_keyboard(vacancy, user_id)
        
        await message.reply_text(
            vacancy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    def get_vacancy_keyboard(self, vacancy, user_id):
        """Создает клавиатуру для вакансии"""
        subscription = self.db.get_subscription(user_id)
        can_apply = subscription['is_premium'] or subscription['free_applications'] > 0
        
        buttons = []
        
        if can_apply:
            buttons.append(InlineKeyboardButton("📨 Apply", callback_data=f"apply_{vacancy['id']}"))
        else:
            buttons.append(InlineKeyboardButton("🔒 Apply (Premium)", callback_data="premium_info"))
        
        buttons.extend([
            InlineKeyboardButton("❤️ Save", callback_data=f"save_{vacancy['id']}"),
            InlineKeyboardButton("👎 Hide", callback_data=f"hide_{vacancy['id']}")
        ])
        
        return [buttons]
    
    async def handle_apply(self, query, context):
        """Обработка отклика на вакансию"""
        user_id = query.from_user.id
        vacancy_id = int(query.data.replace('apply_', ''))
        
        subscription = self.db.get_subscription(user_id)
        
        if not subscription['is_premium'] and subscription['free_applications'] <= 0:
            await query.edit_message_text(
                "❌ У вас закончились бесплатные отклики!\n\n"
                "💎 Перейдите на Premium чтобы откликаться без ограничений:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")]
                ])
            )
            return
        
        # Используем отклик
        if not subscription['is_premium']:
            self.db.update_subscription(user_id, {'free_applications': subscription['free_applications'] - 1})
        
        # Получаем информацию о вакансии
        vacancy = self.db.get_vacancy(vacancy_id)
        if not vacancy:
            await query.answer("Вакансия не найдена")
            return
        
        # Сохраняем действие
        self.db.save_user_action(user_id, vacancy_id, 'applied')
        
        # Показываем информацию для отклика
        apply_text = ""
        if vacancy.get('apply_url'):
            apply_text = f"📨 **Ссылка для отклика:** {vacancy['apply_url']}"
        elif vacancy.get('contacts'):
            apply_text = f"📧 **Контакты:** {vacancy['contacts']}"
        else:
            apply_text = "ℹ️ Контактная информация не указана"
        
        remaining = self.db.get_subscription(user_id)['free_applications']
        remaining_text = f"Осталось откликов: {remaining}" if not subscription['is_premium'] else "Откликов: ∞ (Premium)"
        
        await query.edit_message_text(
            f"📨 **Отклик на вакансию**\n\n"
            f"**{vacancy['title']}** at {vacancy['company']}\n\n"
            f"{apply_text}\n\n"
            f"{remaining_text}",
            parse_mode='Markdown'
        )
    
    async def handle_save(self, query, context):
        """Обработка сохранения вакансии"""
        user_id = query.from_user.id
        vacancy_id = int(query.data.replace('save_', ''))
        
        self.db.save_user_action(user_id, vacancy_id, 'saved')
        await query.answer("✅ Вакансия сохранена!")
    
    async def handle_hide(self, query, context):
        """Обработка скрытия вакансии"""
        user_id = query.from_user.id
        vacancy_id = int(query.data.replace('hide_', ''))
        
        self.db.save_user_action(user_id, vacancy_id, 'hidden')
        await query.answer("✅ Вакансия скрыта!")
    
    async def handle_pagination(self, query, context):
        """Обработка пагинации"""
        page = int(query.data.replace('page_', ''))
        await self.show_feed(query.message, page=page)
    
    async def saved(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /saved - показывает сохраненные вакансии"""
        user_id = update.effective_user.id
        
        saved_ids = self.db.get_user_actions(user_id, 'saved')
        if not saved_ids:
            await update.message.reply_text("У вас нет сохраненных вакансий.")
            return
        
        for vacancy_id in saved_ids[:10]:  # Показываем первые 10
            vacancy = self.db.get_vacancy(vacancy_id)
            if vacancy:
                await self.send_saved_vacancy_message(update.message, vacancy, user_id)
    
    async def send_saved_vacancy_message(self, message, vacancy, user_id):
        """Отправляет сохраненную вакансию"""
        salary_text = ""
        if vacancy.get('salary_min') and vacancy.get('salary_max'):
            salary_text = f"💵 **Salary:** {vacancy['salary_min']} - {vacancy['salary_max']} {vacancy.get('currency', 'USD')}\n"
        
        subscription = self.db.get_subscription(user_id)
        company_text = f"🏢 **Company:** {vacancy['company']}" if subscription['is_premium'] else "🏢 **Company:** [Premium only]"
        
        vacancy_text = f"""
⭐ **Сохраненная вакансия**

🚀 **{vacancy['title']}**

{company_text}
{salary_text}📍 **Location:** {vacancy['location']}

📝 **Description:** {vacancy.get('description_short', '')}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📨 Apply", callback_data=f"apply_{vacancy['id']}"),
                InlineKeyboardButton("🗑️ Удалить", callback_data=f"unsave_{vacancy['id']}")
            ]
        ]
        
        await message.reply_text(
            vacancy_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /subscription - показывает информацию о подписке"""
        user_id = update.effective_user.id
        subscription = self.db.get_subscription(user_id)
        
        if subscription['is_premium']:
            status_text = "✅ Активна"
            applications_text = "Откликов: ∞ (без ограничений)"
        else:
            status_text = "❌ Не активна"
            applications_text = f"Осталось откликов: {subscription['free_applications']}"
        
        text = f"""
💎 **Ваша подписка**

Статус: {status_text}
{applications_text}

**Премиум подписка дает:**
• 🔓 Неограниченные отклики
• 🚀 Ранний доступ к вакансиям
• 📊 Расширенная статистика
• 🔍 Приоритет в поиске
• 👀 Видимость названий компаний

**Стоимость:** $4.99 в месяц
        """
        
        keyboard = []
        if not subscription['is_premium']:
            keyboard.append([InlineKeyboardButton("💎 Апгрейд до Premium", callback_data="premium_info")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_premium_info(self, query):
        """Показывает информацию о премиум подписке"""
        premium_text = """
💎 **Smart Job Bot Premium**

**Что вы получаете:**
• 🔓 Неограниченные отклики на вакансии
• 🚀 Ранний доступ к новым вакансиям  
• 📊 Расширенная статистика профиля
• 🔍 Приоритет в поиске
• 👀 Видимость названий компаний и контактов

**Стоимость:** $4.99 в месяц

Для приобретения Premium подписки обратитесь к @yanovskay_tatsiana
        """
        
        keyboard = [
            [InlineKeyboardButton("💳 Купить Premium ($4.99/мес)", callback_data="buy_premium")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(
            premium_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def handle_buy_premium(self, query):
        """Обработка покупки премиум подписки"""
        user_id = query.from_user.id
        
        # В реальном приложении здесь была бы интеграция с платежной системой
        # Сейчас просто активируем премиум
        self.db.update_subscription(user_id, {
            'is_premium': True,
            'free_applications': 999,
            'premium_until': (datetime.now() + timedelta(days=30)).isoformat()
        })
        
        await query.edit_message_text(
            "🎉 **Поздравляем!**\n\n"
            "Вы успешно активировали Premium подписку!\n\n"
            "Теперь у вас есть:\n"
            "• 🔓 Неограниченные отклики\n"
            "• 🚀 Ранний доступ к вакансиям\n"
            "• 📊 Расширенная статистика\n"
            "• 🔍 Приоритет в поиске\n"
            "• 👀 Видимость компаний и контактов\n\n"
            "Спасибо за доверие!\n\n"
            "По вопросам обращайтесь к @yanovskay_tatsiana",
            parse_mode='Markdown'
        )
    
    async def tools(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /tools - показывает дополнительные сервисы"""
        tools_text = """
🛠 **Дополнительные сервисы**

**Доступные инструменты:**

1. **AI Анализ и создание резюме** - $5
   - Детальный анализ вашего резюме
   - Рекомендации по улучшению
   - Ключевые слова для ATS систем
   - Создание профессионального резюме с нуля

2. **Генерация сопроводительного письма** - $5
   - Персонализированное письмо под конкретную вакансию
   - Подчеркивание релевантного опыта
   - Профессиональный тон и структура
   - Адаптация под требования компании

3. **Подготовка к собеседованию** - $20
   - Вопросы и ответы по вашей роли
   - Технические вопросы и кейсы
   - Советы по самопрезентации
   - Симуляция собеседования с обратной связью

4. **Консультация HR-эксперта** - $50
   - Персональная консультация 1-на-1
   - Разбор профиля и карьерного пути
   - Подготовка к переговорам о зарплате
   - Стратегия поиска работы

**Для заказа услуги напишите @yanovskay_tatsiana**
        """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            tools_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - показывает справку"""
        help_text = """
📖 **Справка по Smart Job Bot**

**Основные команды:**
/start - Начать работу с ботом
/profile - Мой профиль и настройки
/feed - Лента вакансий
/saved - Сохраненные вакансии  
/subscription - Управление подпиской
/tools - Дополнительные сервисы
/help - Эта справка

**Как пользоваться:**
1. Настройте профиль через /start
2. Просматривайте вакансии в /feed
3. Сохраняйте понравившиеся вакансии
4. Откликайтесь на интересные предложения
5. Используйте дополнительные сервисы для улучшения резюме и подготовки

**Система подписок:**
• Бесплатно: 10 откликов, базовый поиск
• Premium ($4.99/мес): неограниченные отклики, ранний доступ, приоритет в поиске

**Поддержка:**
По вопросам работы бота обращайтесь @yanovskay_tatsiana
        """
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
        ]
        
        await update.message.reply_text(
            help_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin - админ панель"""
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_USERS:
            await update.message.reply_text("❌ У вас нет доступа к админ-панели")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton("➕ Добавить вакансию", callback_data="admin_add_vacancy")]
        ]
        
        await update.message.reply_text(
            "🛠️ **Админ-панель**\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_admin_stats(self, query):
        """Показывает статистику для админа"""
        stats = self.db.get_stats()
        
        stats_text = f"""
📊 **Статистика бота**

👥 **Пользователи:** {stats['users_count']}
📋 **Вакансии:** {stats['vacancies_count']}
💎 **Премиум:** {stats['premium_count']}
📨 **Отклики:** {stats['applications_count']}
        """
        
        keyboard = [[InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")]]
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def start_admin_broadcast(self, query, context):
        """Начинает процесс рассылки"""
        await query.edit_message_text(
            "📢 **Рассылка сообщения**\n\n"
            "Отправьте сообщение, которое хотите разослать всем пользователям:"
        )
        context.user_data['admin_action'] = 'broadcast'
    
    async def start_admin_add_vacancy(self, query, context):
        """Начинает процесс добавления вакансии"""
        await query.edit_message_text(
            "➕ **Добавление вакансии**\n\n"
            "Отправьте данные вакансии в формате:\n\n"
            "Название вакансии\n"
            "Компания | Индустрия\n"
            "Зарплата: 3000-4000 USD\n"
            "Локация: Remote / Город\n"
            "Формат: Remote/Hybrid/Office\n"
            "Описание: Краткое описание\n"
            "Требования: Требования к кандидату\n"
            "Контакты: email@example.com или ссылка\n"
        )
        context.user_data['admin_action'] = 'add_vacancy'
    
    def parse_vacancy_from_text(self, text):
        """Парсит вакансию из текстового формата"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if len(lines) < 3:
            return None
        
        vacancy = {}
        
        # Базовые поля
        vacancy['title'] = lines[0]
        
        # Компания и индустрия
        if '|' in lines[1]:
            company_parts = lines[1].split('|')
            vacancy['company'] = company_parts[0].strip()
            vacancy['industry'] = company_parts[1].strip()
        else:
            vacancy['company'] = lines[1]
        
        # Остальные поля
        for line in lines[2:]:
            if line.lower().startswith('зарплата:') or line.lower().startswith('salary:'):
                salary_text = line.split(':', 1)[1].strip()
                if '-' in salary_text and 'USD' in salary_text:
                    try:
                        amounts = salary_text.split('USD')[0].strip().split('-')
                        vacancy['salary_min'] = int(amounts[0].strip())
                        vacancy['salary_max'] = int(amounts[1].strip())
                        vacancy['currency'] = 'USD'
                    except:
                        pass
            elif line.lower().startswith('локация:') or line.lower().startswith('location:'):
                vacancy['location'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('формат:') or line.lower().startswith('format:'):
                vacancy['work_format'] = line.split(':', 1)[1].strip().lower()
            elif line.lower().startswith('описание:') or line.lower().startswith('description:'):
                vacancy['description_short'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('требования:') or line.lower().startswith('requirements:'):
                vacancy['requirements'] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('контакты:') or line.lower().startswith('contacts:'):
                contacts = line.split(':', 1)[1].strip()
                vacancy['contacts'] = contacts
                if contacts.startswith('http'):
                    vacancy['apply_url'] = contacts
        
        # Заполняем обязательные поля по умолчанию
        if 'location' not in vacancy:
            vacancy['location'] = 'Remote'
        if 'work_format' not in vacancy:
            vacancy['work_format'] = 'remote'
        if 'source' not in vacancy:
            vacancy['source'] = 'admin'
        
        return vacancy
    
    def get_all_users(self):
        """Получает всех пользователей"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    
    def run(self):
        """Запуск бота"""
        print("🤖 Бот запускается...")
        print(f"👤 Админы: {ADMIN_USERS}")
        print("🔗 Напишите боту в Telegram: /start")
        self.application.run_polling()

def main():
    """Основная функция"""
    print("🚀 Запуск Smart Job Bot")
    print("🎯 Создано для @yanovskay_tatsiana")
    
    if not ADMIN_USERS:
        print("⚠️  ВНИМАНИЕ: Не настроены администраторы!")
        print("📱 Добавьте ваш user_id в переменную ADMIN_USERS")
    
    try:
        bot = SmartJobBot(BOT_TOKEN)
        bot.run()
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
