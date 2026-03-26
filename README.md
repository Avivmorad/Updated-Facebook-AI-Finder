# Facebook Groups Post Finder & Matcher

## מה זה?

זו תוכנה שמחפשת פוסטים רלוונטיים בפיד הקבוצות של Facebook לפי מה שאתה מחפש.

היא עושה את זה כך:
- פותחת את Facebook עם פרופיל Chrome קיים שלך. (כלומר: לא עושה login לבד)
- סורקת פוסטים מהפיד.
- פותחת כל פוסט.
- לוקחת רק:
  - טקסט הפוסט
  - תמונות
  - תאריך פרסום
  - קישור לפוסט
- שולחת את המידע ל־AI.
- שומרת רק פוסטים רלוונטיים.
- מדרגת אותם לפי `match_score`.

## שלושת הקבצים החשובים בשורש

- `README.md`  
  זה ההסבר. (אם שכחת איך מריצים, חוזרים לפה)

- `start.py`  
  זה הקובץ שמריצים. (זה "כפתור ההפעלה" הראשי)

- `settings.py`  
  זה הקובץ שמשנים. (פה משנים query, מצב הרצה, debugging ועוד)

## הכי פשוט בעולם

1. פתח את `settings.py`
2. שים שם משהו כזה:

```python
DEBUGGING = True          # מראה בטרמינל מה התוכנה עושה, צעד אחרי צעד
RUN_MODE = "query"        # אומר לתוכנה להשתמש בטקסט של QUERY
QUERY = "iphone 13"       # מה שאתה מחפש
MAX_POSTS = 10            # כמה פוסטים לבדוק לכל היותר
OUTPUT_JSON = "data/reports/latest.json"  # איפה לשמור את התוצאה
```

3. הרץ:

```bash
python start.py
```

4. מה אמור לקרות:
- אם `DEBUGGING = True`, תראה בטרמינל הסבר ברור של כל שלב. (מה נפתח, מה נסרק, מה נפסל, מה נשמר)
- בסוף תראה:
  - `Total results: ...`
  - `Saved JSON report: ...`

## מה צריך להתקין פעם אחת

הרץ:

```bash
pip install -r requirements/runtime.txt
pip install -r requirements/dev.txt
playwright install
```

מה זה עושה:
- `requirements/runtime.txt`  
  מתקין את מה שהתוכנית צריכה כדי לרוץ.

- `requirements/dev.txt`  
  מתקין כלים לבדיקות. (לא חובה להרצה רגילה, כן טוב לפיתוח)

- `playwright install`  
  מתקין את רכיבי הדפדפן ש־Playwright צריך.

## מה צריך להכין פעם אחת

### 1. קובץ `.env`

צריך שיהיה לך `.env` עם ההגדרות החשובות.

הכי חשוב:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
CHROME_USER_DATA_DIR=C:/path/to/copied/chrome_user_data
CHROME_PROFILE_DIRECTORY=Default
```

הסבר קצר:
- `AI_PROVIDER`  
  באיזה ספק AI להשתמש. (כרגע בעיקר `groq` או `gemini`)

- `GROQ_API_KEY` / `GEMINI_API_KEY`  
  המפתח של ה־AI. (בלי זה ה־AI לא יעבוד)

- `CHROME_USER_DATA_DIR`  
  תיקיית פרופיל Chrome מועתקת. (לא התיקייה המקורית של Chrome)

- `CHROME_PROFILE_DIRECTORY`  
  שם הפרופיל בתוך התיקייה. (לרוב `Default` או `Profile 1` וכדומה)

### 2. פרופיל Chrome מחובר ל־Facebook

התוכנה לא מתחברת לבד ל־Facebook.

כלומר:
- אתה צריך פרופיל Chrome שכבר מחובר לפייסבוק.
- עדיף עותק של פרופיל, לא הפרופיל הראשי המקורי.

אם צריך להכין עותק כזה:

```bash
python scripts/bootstrap_chrome_profile.py "C:/Users/You/AppData/Local/Google/Chrome/User Data/Profile 5"
```

זה רק עוזר להעתיק פרופיל. (כדי שהתוכנה תשתמש בו בצורה בטוחה)

## איך משנים את ההרצה ב־`settings.py`

זה הקובץ המרכזי לעריכה.

הקובץ נראה כך:

```python
DEBUGGING = False

RUN_MODE = "file"         # אפשר: "file", "query", "interactive", "demo"
QUERY = "iphone 13"       # בשימוש רק אם RUN_MODE = "query"
INPUT_FILE = "data/sample_search_input.json"  # בשימוש רק אם RUN_MODE = "file"

MAX_POSTS = 20
OUTPUT_JSON = "data/reports/latest.json"
```

### מה כל שדה עושה

- `DEBUGGING`  
  `True` = מסביר בטרמינל מה קורה שלב־שלב.  
  `False` = פלט קצר יותר.

- `RUN_MODE`  
  בוחר מאיפה הקלט יגיע.

- `QUERY`  
  הטקסט שאתה מחפש. (רק במצב `query`)

- `INPUT_FILE`  
  קובץ JSON שממנו קוראים קלט. (רק במצב `file`)

- `MAX_POSTS`  
  כמה פוסטים לבדוק לכל היותר.  
  מספר קטן = ריצה מהירה יותר.

- `OUTPUT_JSON`  
  איפה לשמור את תוצאת הריצה.

## מצבי הרצה

### מצב 1: `query`

הכי טוב לבדיקה מהירה.

שים:

```python
RUN_MODE = "query"
QUERY = "iphone 13"
```

ואז:

```bash
python start.py
```

### מצב 2: `file`

טוב אם אתה רוצה לשמור קלט קבוע בקובץ.

שים:

```python
RUN_MODE = "file"
INPUT_FILE = "data/sample_search_input.json"
```

דוגמה לתוכן הקובץ:

```json
{
  "query": "iphone 13"
}
```

ואז:

```bash
python start.py
```

### מצב 3: `interactive`

טוב אם אתה רוצה שורת קלט ידנית כל פעם.

שים:

```python
RUN_MODE = "interactive"
```

ואז:

```bash
python start.py
```

מה תראה:
- התוכנה תשאל אותך `Search query:`
- אתה כותב מה לחפש ולוחץ Enter

### מצב 4: `demo`

טוב רק לבדיקה מהירה של המסלול.

שים:

```python
RUN_MODE = "demo"
```

ואז:

```bash
python start.py
```

## מה רואים בטרמינל

### אם `DEBUGGING = False`

תראה רק את הדברים החשובים:
- כמה תוצאות נמצאו
- איפה נשמר קובץ ה־JSON
- אזהרות או שגיאות אם היו

### אם `DEBUGGING = True`

תראה הסבר אנושי יותר, למשל:
- באיזה מצב ריצה התחיל
- האם ההגדרות תקינות
- כמה פוסטים נמצאו
- איזה פוסט נפתח
- אם פוסט נפסל בגלל זמן
- אם ה־AI החליט שפוסט לא רלוונטי
- כמה תוצאות נשארו בסוף

זה נועד כדי שתוכל לקרוא את הטרמינל ולהבין "מה קרה" בלי להיכנס לקוד.

## איך להריץ בדיקות

### בדיקה של הסביבה

הרץ:

```bash
python scripts/run_app.py --mode doctor
```

מה זה עושה:
- בודק Python
- בודק `.env`
- בודק dependencies
- בודק Playwright
- בודק תיקיות כתיבה

מה אתה מצפה לראות:
- הרבה שורות של `[OK]`
- בסוף:
  - `Doctor finished successfully ...`

### בדיקה של Facebook session

הרץ:

```bash
python scripts/run_app.py --mode doctor-session
```

מה זה עושה:
- בודק אם הפרופיל של Chrome באמת מחובר ל־Facebook

אם זה לא עובד:
- כנראה שהפרופיל לא מחובר
- או ש־Chrome פתוח ונועל את התיקייה

### בדיקות קוד אוטומטיות

הרץ:

```bash
pytest -c tests/pytest.ini -q
```

מה אתה מצפה לראות:
- נקודות `....`
- ואז `passed`

אם יש כשל:
- אחד הטסטים נשבר
- צריך לקרוא את השגיאה ולתקן

## עוד פקודות שימושיות

### הרצה דרך helper launcher

```bash
python scripts/run_app.py --mode start
```

זה פשוט מריץ את `start.py`. (נוח אם אתה אוהב לעבוד דרך launcher)

```bash
python scripts/run_app.py --mode test
```

זה מריץ את כל הטסטים.

```bash
python scripts/run_app.py --mode file
```

זה מריץ את ה־CLI במצב file.

## איפה נשמרות התוצאות

- קובץ JSON נשמר לפי `OUTPUT_JSON`
- ברירת המחדל היא:

```text
data/reports/latest.json
```

- לוגים נשמרים ב:

```text
data/logs/app.log
```

- היסטוריית ריצות נשמרת ב:

```text
data/run_history.json
```

## בעיות נפוצות

### 1. ה־AI לא עובד

בדוק:
- שיש `GROQ_API_KEY` או `GEMINI_API_KEY`
- שה־`AI_PROVIDER` תואם למפתח

### 2. Facebook לא נפתח נכון

בדוק:
- שהנתיב ב־`CHROME_USER_DATA_DIR` נכון
- שזה עותק של פרופיל, לא תיקיית Chrome הראשית
- שה־`CHROME_PROFILE_DIRECTORY` נכון

### 3. התוכנית אומרת שהפרופיל נעול

סגור את כל חלונות Chrome.  
לפעמים צריך לסגור גם מה־system tray.

### 4. אין תוצאות

יכול להיות ש:
- לא נמצאו פוסטים רלוונטיים
- הפילטר של 24 שעות פסל את הפוסטים
- ה־AI החליט שהפוסטים לא מתאימים

### 5. קובץ קלט לא נמצא

בדוק שהנתיב ב־`INPUT_FILE` נכון.

## אם אתה רק רוצה לזכור דבר אחד

- משנים: `settings.py`
- מריצים: `python start.py`
- אם רוצים לראות הכול: `DEBUGGING = True`
- אם רוצים לבדוק שהכול תקין: `python scripts/run_app.py --mode doctor`

## למפתחים

מסמכי האפיון נמצאים ב:
- `docs/specs/AGENTS.md`
- `docs/specs/SYSTEM_DESIGN.md`
- `docs/specs/PROJECT_DEVELOPMENT_PHASES.md`
- `docs/specs/TASKS.md`
