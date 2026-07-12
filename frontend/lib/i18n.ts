/**
 * Phase C of the MVP roadmap: "Arabic, for real this time... over 60% of
 * the population speaks Arabic day-to-day; this was correctly scoped out
 * of v1 to control build size, but a market-fit product can't defer it
 * indefinitely."
 *
 * Scope: the app chrome (nav, page headers/subtitles, buttons, auth forms)
 * is translated and the layout mirrors for RTL. Data values pulled from
 * the backend -- community names, transaction figures, agent-generated
 * memo text -- are deliberately left as-is: those are either proper nouns
 * (community/building names aren't conventionally translated in Dubai
 * real estate listings either language) or would need the LLM prompts
 * themselves localized, which is a separate, larger effort than "the UI
 * has an Arabic mode."
 */

export type Locale = "en" | "ar";

export const LOCALES: Locale[] = ["en", "ar"];

export const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  ar: "العربية",
};

type Dict = Record<string, string>;

const en: Dict = {
  "app.title": "Sakan AI",
  "app.subtitle": "deal intelligence terminal",

  "nav.commandDeck": "Command Deck",
  "nav.comps": "Comps Explorer",
  "nav.analytics": "Analytics",
  "nav.billing": "Billing",

  "home.eyebrow": "Deal Intelligence Terminal",
  "home.title": "Ask Sakan a deal question.",
  "home.subtitle":
    "Plain English in — cited comps, a defensible valuation, a RERA compliance check, and a ready-to-send memo out. Every claim shows its work.",
  "home.marketSnapshot": "Market snapshot",

  "comps.title": "Comps Explorer",
  "comps.subtitle": "Search and filter the seeded transaction dataset directly.",

  "market.title": "Analytics",
  "market.subtitle":
    "Price trends, developer track record, and off-plan sell-through — aggregated from the seeded transaction dataset.",

  "billing.title": "Billing",
  "billing.subtitle":
    "Pricing is directional and validated with design partners before it's final — see the MVP roadmap.",
  "billing.currentPlan": "Current plan",
  "billing.manageSubscription": "Manage subscription",
  "billing.logInPrompt": "to see your current plan and usage.",
  "billing.logIn": "Log in",

  "auth.signIn": "Sign in",
  "auth.signOut": "Sign out",
  "auth.email": "Email",
  "auth.password": "Password",
  "auth.needAccount": "Need an account? Create one",
  "auth.haveAccount": "Already have an account? Sign in",
  "auth.createYourAccount": "Create your account",
  "auth.welcomeBack": "Welcome back",
  "auth.getStarted": "Get started",
  "auth.signInDescription": "Sign in to run a deal query and see your saved memos.",
  "auth.registerDescription": "A free account gets you unlimited comps search and 50 full-pipeline queries a month.",
  "auth.fullNameOptional": "Full name (optional)",
  "auth.emailPlaceholder": "you@brokerage.ae",
  "auth.createAccount": "Create account",
  "auth.pleaseWait": "Please wait…",

  "query.placeholder": "e.g. 2BR apartment in Dubai Marina under 2.2M, off-plan compliance check",
  "query.submit": "Ask Sakan",
};

const ar: Dict = {
  "app.title": "سكن AI",
  "app.subtitle": "منصة تحليل الصفقات العقارية",

  "nav.commandDeck": "لوحة التحكم",
  "nav.comps": "مستكشف المقارنات",
  "nav.analytics": "التحليلات",
  "nav.billing": "الفوترة",

  "home.eyebrow": "منصة تحليل الصفقات العقارية",
  "home.title": "اسأل سكن عن صفقة عقارية.",
  "home.subtitle":
    "اكتب سؤالك بلغة طبيعية — واحصل على مقارنات موثّقة، وتقييم قابل للدفاع عنه، وفحص امتثال لهيئة التنظيم العقاري (RERA)، ومذكرة جاهزة للإرسال. كل ادعاء يوثّق مصدره.",
  "home.marketSnapshot": "لمحة عن السوق",

  "comps.title": "مستكشف المقارنات",
  "comps.subtitle": "ابحث وصفِّ بيانات المعاملات المرجعية مباشرة.",

  "market.title": "التحليلات",
  "market.subtitle":
    "اتجاهات الأسعار، وسجل أداء المطورين، ومعدلات بيع المشاريع على الخارطة — مجمّعة من بيانات المعاملات المرجعية.",

  "billing.title": "الفوترة",
  "billing.subtitle":
    "الأسعار المعروضة استرشادية وسيتم التحقق منها مع شركاء التصميم قبل اعتمادها نهائيًا — راجع خارطة الطريق.",
  "billing.currentPlan": "الباقة الحالية",
  "billing.manageSubscription": "إدارة الاشتراك",
  "billing.logInPrompt": "لعرض باقتك الحالية واستخدامك.",
  "billing.logIn": "تسجيل الدخول",

  "auth.signIn": "تسجيل الدخول",
  "auth.signOut": "تسجيل الخروج",
  "auth.email": "البريد الإلكتروني",
  "auth.password": "كلمة المرور",
  "auth.needAccount": "ليس لديك حساب؟ أنشئ واحدًا",
  "auth.haveAccount": "لديك حساب بالفعل؟ سجّل الدخول",
  "auth.createYourAccount": "أنشئ حسابك",
  "auth.welcomeBack": "مرحبًا بعودتك",
  "auth.getStarted": "ابدأ الآن",
  "auth.signInDescription": "سجّل الدخول لتشغيل استعلام صفقة وعرض مذكراتك المحفوظة.",
  "auth.registerDescription": "يمنحك الحساب المجاني بحث مقارنات غير محدود و٥٠ استعلامًا كاملاً شهريًا.",
  "auth.fullNameOptional": "الاسم الكامل (اختياري)",
  "auth.emailPlaceholder": "you@brokerage.ae",
  "auth.createAccount": "إنشاء حساب",
  "auth.pleaseWait": "يرجى الانتظار…",

  "query.placeholder": "مثال: شقة غرفتي نوم في دبي مارينا بأقل من 2.2 مليون، فحص امتثال لمشروع على الخارطة",
  "query.submit": "اسأل سكن",
};

export const DICTIONARIES: Record<Locale, Dict> = { en, ar };

export function translate(locale: Locale, key: string): string {
  return DICTIONARIES[locale][key] ?? DICTIONARIES.en[key] ?? key;
}

export function dirFor(locale: Locale): "rtl" | "ltr" {
  return locale === "ar" ? "rtl" : "ltr";
}
