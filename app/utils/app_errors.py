from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class AppErrorTemplate:
    code: str
    summary_he: str
    cause_he: str
    action_he: str


ERROR_CATALOG: Dict[str, AppErrorTemplate] = {
    "ERR_INPUT_MODE_INVALID": AppErrorTemplate(
        code="ERR_INPUT_MODE_INVALID",
        summary_he="בחירת מצב קלט אינה תקינה",
        cause_he="נבחרו כמה מצבי קלט יחד או ערך RUN_MODE לא תקין",
        action_he="בחר מצב קלט אחד בלבד ונסה שוב",
    ),
    "ERR_INPUT_QUERY_MISSING": AppErrorTemplate(
        code="ERR_INPUT_QUERY_MISSING",
        summary_he="שדה החיפוש חסר או ריק",
        cause_he="לא התקבל ערך תקין עבור query",
        action_he="העבר קובץ קלט עם query לא ריק או הגדר QUERY תקין",
    ),
    "ERR_INPUT_FILE_NOT_FOUND": AppErrorTemplate(
        code="ERR_INPUT_FILE_NOT_FOUND",
        summary_he="קובץ הקלט לא נמצא",
        cause_he="הנתיב שהוגדר ל-INPUT_FILE לא קיים",
        action_he="בדוק את הנתיב בקובץ settings.py או העבר נתיב קיים",
    ),
    "ERR_INPUT_JSON_INVALID": AppErrorTemplate(
        code="ERR_INPUT_JSON_INVALID",
        summary_he="קובץ הקלט אינו JSON תקין",
        cause_he="הקובץ נטען אבל פורמט ה-JSON לא חוקי",
        action_he="תקן את מבנה ה-JSON בקובץ הקלט ונסה שוב",
    ),
    "ERR_BROWSER_USER_DATA_DIR_MISSING": AppErrorTemplate(
        code="ERR_BROWSER_USER_DATA_DIR_MISSING",
        summary_he="תיקיית נתוני המשתמש של Chrome לא הוגדרה או לא קיימת",
        cause_he="CHROME_USER_DATA_DIR ריק או מצביע לנתיב שאינו קיים",
        action_he="הגדר CHROME_USER_DATA_DIR נכון בקובץ .env",
    ),
    "ERR_BROWSER_PROFILE_DIR_MISSING": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_DIR_MISSING",
        summary_he="תיקיית הפרופיל של Chrome לא נמצאה",
        cause_he="CHROME_PROFILE_DIRECTORY לא קיים בתוך CHROME_USER_DATA_DIR",
        action_he="בדוק את שם הפרופיל המדויק והגדר אותו מחדש ב-.env",
    ),
    "ERR_BROWSER_PROFILE_LOCKED": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_LOCKED",
        summary_he="פרופיל Chrome נעול על ידי חלון Chrome אחר",
        cause_he="Chrome פעיל ומשאיר lock file על התיקייה",
        action_he="סגור את כל חלונות Chrome (כולל tray) ונסה שוב",
    ),
    "ERR_BROWSER_PROFILE_INCOMPATIBLE": AppErrorTemplate(
        code="ERR_BROWSER_PROFILE_INCOMPATIBLE",
        summary_he="לא ניתן לפתוח את פרופיל Chrome שהוגדר",
        cause_he="הפרופיל שהועתק לא תואם או פגום עבור Playwright",
        action_he="צור מחדש פרופיל מועתק, התחבר לפייסבוק ידנית ונסה שוב",
    ),
    "ERR_FACEBOOK_HOME_OPEN_FAILED": AppErrorTemplate(
        code="ERR_FACEBOOK_HOME_OPEN_FAILED",
        summary_he="לא ניתן לפתוח את עמוד הבית של פייסבוק",
        cause_he="ניווט לפייסבוק נכשל או חזר סטטוס HTTP לא תקין",
        action_he="בדוק חיבור רשת ותקינות פרופיל Chrome והרץ שוב",
    ),
    "ERR_FACEBOOK_NOT_LOGGED_IN": AppErrorTemplate(
        code="ERR_FACEBOOK_NOT_LOGGED_IN",
        summary_he="פייסבוק לא מחובר בפרופיל שנבחר",
        cause_he="המערכת זיהתה דף התחברות או מצב checkpoint",
        action_he="פתח את אותו פרופיל Chrome ידנית, התחבר לפייסבוק ונסה שוב",
    ),
    "ERR_GROUPS_FEED_OPEN_FAILED": AppErrorTemplate(
        code="ERR_GROUPS_FEED_OPEN_FAILED",
        summary_he="לא ניתן לפתוח את פיד הקבוצות בפייסבוק",
        cause_he="ניווט ל-groups feed נכשל או הסתיים בעמוד לא תקין",
        action_he="בדוק שהקישור לפיד תקין ושהחשבון מחובר לקבוצות",
    ),
    "ERR_FILTER_RECENT_NOT_FOUND": AppErrorTemplate(
        code="ERR_FILTER_RECENT_NOT_FOUND",
        summary_he="לא נמצא פילטר 'פוסטים אחרונים'",
        cause_he="הסלקטורים/כפתורים בפייסבוק לא אותרו בתצוגה הנוכחית",
        action_he="המשך ריצה; הפילטר הקשיח בקוד עדיין יאכוף סינון זמן",
    ),
    "ERR_FILTER_LAST24_NOT_FOUND": AppErrorTemplate(
        code="ERR_FILTER_LAST24_NOT_FOUND",
        summary_he="לא נמצא פילטר '24 שעות אחרונות'",
        cause_he="הכפתור לא הופיע או לא היה לחיץ בממשק הנוכחי",
        action_he="המשך ריצה; סינון 24 שעות בקוד יופעל בכל מקרה",
    ),
    "ERR_GROUPS_SCAN_FAILED": AppErrorTemplate(
        code="ERR_GROUPS_SCAN_FAILED",
        summary_he="סריקת פיד הקבוצות נכשלה",
        cause_he="כל ניסיונות הסריקה הסתיימו בכישלון",
        action_he="בדוק חיבור, פרופיל Chrome והרשאות גישה לקבוצות ונסה שוב",
    ),
    "ERR_NO_POST_LINKS_FOUND": AppErrorTemplate(
        code="ERR_NO_POST_LINKS_FOUND",
        summary_he="לא נמצאו קישורי פוסטים בסריקה",
        cause_he="לא זוהו כרטיסי פוסטים עם לינקים מתאימים",
        action_he="נסה להגדיל max scroll rounds או להריץ שוב בזמן פעילות גבוהה",
    ),
    "ERR_POST_LINK_MISSING": AppErrorTemplate(
        code="ERR_POST_LINK_MISSING",
        summary_he="לפוסט חסר קישור פתיחה",
        cause_he="אובייקט הפוסט שהתקבל לא כולל post_link תקין",
        action_he="דלג על הפוסט ובדוק את שכבת הסריקה שמחזירה לינקים",
    ),
    "ERR_POST_PAGE_LOAD_FAILED": AppErrorTemplate(
        code="ERR_POST_PAGE_LOAD_FAILED",
        summary_he="דף הפוסט לא נטען בהצלחה",
        cause_he="ניווט לפוסט נכשל או חזר HTTP לא תקין",
        action_he="נסה שוב; אם חוזר, בדוק שהקישור תקין ונגיש בחשבון המחובר",
    ),
    "ERR_POST_TEXT_NOT_FOUND": AppErrorTemplate(
        code="ERR_POST_TEXT_NOT_FOUND",
        summary_he="לא נמצא טקסט לפוסט",
        cause_he="לא אותר אלמנט טקסט מתאים לפי הסלקטורים הקיימים",
        action_he="המשך ריצה; ה-AI יקבל גם תמונות ונתונים אחרים אם קיימים",
    ),
    "ERR_POST_IMAGES_NOT_FOUND": AppErrorTemplate(
        code="ERR_POST_IMAGES_NOT_FOUND",
        summary_he="לא נמצאו תמונות לפוסט",
        cause_he="לא אותרו תמונות או שלפוסט אין תמונות בכלל",
        action_he="המשך ריצה; ניתוח ה-AI יתבסס על הטקסט בלבד",
    ),
    "ERR_POST_PUBLISH_DATE_MISSING": AppErrorTemplate(
        code="ERR_POST_PUBLISH_DATE_MISSING",
        summary_he="לא נמצא תאריך פרסום לפוסט",
        cause_he="לא אותר timestamp בעמוד הפוסט",
        action_he="המשך ריצה; אם קיים preview מהפיד הוא ישמש כ-fallback",
    ),
    "ERR_POST_PUBLISH_DATE_UNPARSEABLE": AppErrorTemplate(
        code="ERR_POST_PUBLISH_DATE_UNPARSEABLE",
        summary_he="תאריך הפרסום לא ניתן לפענוח",
        cause_he="פורמט התאריך שחולץ לא נתמך על ידי parser הזמן",
        action_he="דלג על הפוסט או עדכן parser לפורמט זמן חדש",
    ),
    "ERR_POST_TOO_OLD": AppErrorTemplate(
        code="ERR_POST_TOO_OLD",
        summary_he="הפוסט נפסל כי הוא ישן מ-24 שעות",
        cause_he="סינון הזמן הקשיח סימן שהפוסט מחוץ לטווח הזמן",
        action_he="אין פעולה נדרשת; המערכת ממשיכה לפוסט הבא",
    ),
    "ERR_AI_REQUEST_FAILED": AppErrorTemplate(
        code="ERR_AI_REQUEST_FAILED",
        summary_he="קריאת ה-AI נכשלה",
        cause_he="הספק החיצוני החזיר שגיאה או לא ענה בזמן",
        action_he="נסה שוב; אם חוזר בדוק API key, provider, model, ורשת",
    ),
    "ERR_AI_RESPONSE_EMPTY": AppErrorTemplate(
        code="ERR_AI_RESPONSE_EMPTY",
        summary_he="ה-AI החזיר תשובה ריקה",
        cause_he="הספק החזיר טקסט ריק במקום JSON",
        action_he="נסה שוב או בדוק מגבלות ספק/מודל",
    ),
    "ERR_AI_RESPONSE_INVALID_JSON": AppErrorTemplate(
        code="ERR_AI_RESPONSE_INVALID_JSON",
        summary_he="ה-AI החזיר תשובה שלא ניתנת לקריאה כ-JSON",
        cause_he="המודל החזיר טקסט חופשי במקום JSON תקין",
        action_he="נסה שוב ואם זה קבוע בדוק model/provider או צמצם payload",
    ),
    "ERR_AI_RESPONSE_SCHEMA_INVALID": AppErrorTemplate(
        code="ERR_AI_RESPONSE_SCHEMA_INVALID",
        summary_he="תשובת ה-AI לא עומדת בסכימה הנדרשת",
        cause_he="חסרים שדות חובה או יש שדות לא צפויים/טיפוסים שגויים",
        action_he="הרץ שוב; אם חוזר עדכן prompt או parser כך שיחייבו סכימה",
    ),
    "ERR_AI_MARKED_NOT_RELEVANT": AppErrorTemplate(
        code="ERR_AI_MARKED_NOT_RELEVANT",
        summary_he="ה-AI סימן שהפוסט לא רלוונטי",
        cause_he="is_relevant חזר false עבור הפוסט",
        action_he="אין פעולה נדרשת; המערכת מדלגת לפוסט הבא",
    ),
    "ERR_RESULT_SAVE_FAILED": AppErrorTemplate(
        code="ERR_RESULT_SAVE_FAILED",
        summary_he="שמירת קובץ התוצאות נכשלה",
        cause_he="כתיבה לדיסק או הרשאות קובץ נכשלו",
        action_he="בדוק הרשאות כתיבה ונתיב יעד תקין ונסה שוב",
    ),
    "ERR_DEBUG_TRACE_SAVE_FAILED": AppErrorTemplate(
        code="ERR_DEBUG_TRACE_SAVE_FAILED",
        summary_he="שמירת קובץ ה-debug trace נכשלה",
        cause_he="לא ניתן לכתוב לקובץ trace",
        action_he="בדוק הרשאות לנתיב trace; הריצה תמשיך עם הדפסה לטרמינל בלבד",
    ),
    "ERR_RUN_HISTORY_SAVE_FAILED": AppErrorTemplate(
        code="ERR_RUN_HISTORY_SAVE_FAILED",
        summary_he="שמירת היסטוריית ריצות נכשלה",
        cause_he="כתיבה לקובץ run_history נכשלה",
        action_he="בדוק הרשאות כתיבה ותקינות הנתיב data/run_history.json",
    ),
    "ERR_PIPELINE_UNEXPECTED": AppErrorTemplate(
        code="ERR_PIPELINE_UNEXPECTED",
        summary_he="אירעה שגיאה לא צפויה בצינור העיבוד",
        cause_he="רכיב פנימי זרק חריגה שלא סווגה מראש",
        action_he="בדוק לוגים ו-debug trace ונסה שוב",
    ),
}


@dataclass
class AppError(Exception):
    code: str
    summary_he: str
    cause_he: str
    action_he: str
    technical_details: str = ""

    def __str__(self) -> str:
        return f"{self.code}: {self.summary_he}"

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "summary_he": self.summary_he,
            "cause_he": self.cause_he,
            "action_he": self.action_he,
            "technical_details": self.technical_details,
        }


def make_app_error(
    code: str,
    summary_he: Optional[str] = None,
    cause_he: Optional[str] = None,
    action_he: Optional[str] = None,
    technical_details: str = "",
) -> AppError:
    template = ERROR_CATALOG.get(code)
    resolved_summary = (summary_he or (template.summary_he if template else "אירעה שגיאה בתהליך")).strip()
    resolved_cause = (cause_he or (template.cause_he if template else "לא סופקה סיבה מפורטת")).strip()
    resolved_action = (action_he or (template.action_he if template else "בדוק לוגים ונסה שוב")).strip()
    return AppError(
        code=str(code).strip() or "ERR_UNKNOWN",
        summary_he=resolved_summary,
        cause_he=resolved_cause,
        action_he=resolved_action,
        technical_details=technical_details.strip(),
    )


def normalize_app_error(
    exc: Exception,
    *,
    default_code: str,
    default_summary_he: Optional[str] = None,
    default_cause_he: Optional[str] = None,
    default_action_he: Optional[str] = None,
) -> AppError:
    if isinstance(exc, AppError):
        return exc
    return make_app_error(
        code=default_code,
        summary_he=default_summary_he,
        cause_he=default_cause_he,
        action_he=default_action_he,
        technical_details=str(exc),
    )


def find_first_app_error(*errors: Exception) -> Optional[AppError]:
    for err in errors:
        if isinstance(err, AppError):
            return err
    return None


def render_app_error_text(error: AppError, *, include_technical_details: bool = True) -> str:
    lines = [
        f"{error.code} | {error.summary_he}",
        f"סיבה: {error.cause_he}",
        f"מה לעשות: {error.action_he}",
    ]
    if include_technical_details and error.technical_details:
        lines.append(f"פרטים טכניים: {error.technical_details}")
    return "\n".join(lines)
