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
  "nav.deals": "My Deals",
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
  "auth.forgotPassword": "Forgot your password?",
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

  "agentTrace.title": "Agent Trace",
  "agentTrace.query": "Query",
  "agentTrace.comps": "Comps",
  "agentTrace.valuation": "Valuation",
  "agentTrace.compliance": "Compliance",
  "agentTrace.memo": "Memo",
  "agentTrace.failed": "This query failed to complete.",
  "agentTrace.retry": "Retry",
  "agentTrace.retrying": "Retrying…",

  "valuation.title": "Valuation Range",
  "valuation.method": "Method",
  "valuation.notYetComputed": "Not yet computed.",

  "compliance.title": "Compliance",
  "compliance.notYetChecked": "Not yet checked.",
  "compliance.retrievedClauses": "Retrieved clauses",
  "compliance.reviewedBy": "reviewed —",
  "compliance.unreviewed": "unreviewed",
  "compliance.pendingReview": "pending review",
  "compliance.disclaimer":
    "Every clause behind this answer is AI-drafted and has not been reviewed by a licensed legal partner. Treat this as a starting point for manual RERA verification, not legal advice.",

  "comps.comparableTransactions": "Comparable Transactions",
  "comps.noComps": "No comparable transactions retrieved yet.",
  "comps.colTransaction": "Transaction",
  "comps.colBuilding": "Building",
  "comps.colBeds": "Beds",
  "comps.colPrice": "Price",
  "comps.colPricePerSqft": "AED/sqft",
  "comps.colDate": "Date",
  "comps.colSource": "Source",
  "comps.provenanceSynthetic": "Demo data",
  "comps.provenanceDldKaggle": "DLD (public)",
  "comps.provenanceDldOpenFree": "DLD (official)",
  "comps.provenanceLicensedPartner": "Licensed",

  "footer.tagline": "Agentic deal intelligence for Dubai real estate. Every claim shows its work.",
  "footer.product": "Product",
  "footer.pricing": "Pricing",
  "footer.guides": "Market guides",
  "footer.status": "System status",
  "footer.legal": "Legal",
  "footer.terms": "Terms of Service",
  "footer.privacy": "Privacy Policy",
  "footer.dpa": "Data Processing Addendum",
  "footer.contact": "Contact",
  "footer.contactSales": "Contact sales",
  "footer.dataNotice": "Demo runs on synthetic and public-dataset data — see the data sources in our documentation.",
  "footer.rights": "All rights reserved.",

  "pricing.eyebrow": "Pricing",
  "pricing.title": "Simple, transparent pricing.",
  "pricing.subtitle":
    "Start free with unlimited comps search. Upgrade when you need more full-pipeline deal queries.",
  "pricing.getStarted": "Get started",
  "pricing.contactSales": "Contact sales",
  "pricing.faqTitle": "Common questions",

  "legal.draftBanner":
    "Draft — pending legal review. This page is a placeholder template, not a reviewed or binding legal document. Do not rely on it until counsel has signed off.",
  "legal.lastUpdated": "Last updated",

  "home.howItWorks": "How it works",
  "home.step1Title": "Ask in plain English",
  "home.step1Body": "\"2BR in Business Bay under AED 2M\" — no forms, no filters to configure first.",
  "home.step2Title": "Agents pull comps and value it",
  "home.step2Body": "Real comparable transactions, a statistical model, and a defensible valuation range.",
  "home.step3Title": "Compliance check + cited memo",
  "home.step3Body": "RERA clauses retrieved and cited, or an honest \"unable to verify\" — never a guess.",
  "home.pricingTeaser": "Free to start. Unlimited comps search on every plan.",
  "home.viewPricing": "View pricing",
};

const ar: Dict = {
  "app.title": "سكن AI",
  "app.subtitle": "منصة تحليل الصفقات العقارية",

  "nav.commandDeck": "لوحة التحكم",
  "nav.comps": "مستكشف المقارنات",
  "nav.analytics": "التحليلات",
  "nav.deals": "صفقاتي",
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
  "auth.forgotPassword": "نسيت كلمة المرور؟",
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

  "agentTrace.title": "مسار الوكلاء",
  "agentTrace.query": "الاستعلام",
  "agentTrace.comps": "المقارنات",
  "agentTrace.valuation": "التقييم",
  "agentTrace.compliance": "الامتثال",
  "agentTrace.memo": "المذكرة",
  "agentTrace.failed": "تعذّر إكمال هذا الاستعلام.",
  "agentTrace.retry": "إعادة المحاولة",
  "agentTrace.retrying": "جارٍ إعادة المحاولة…",

  "valuation.title": "نطاق التقييم",
  "valuation.method": "الطريقة",
  "valuation.notYetComputed": "لم يُحتسب بعد.",

  "compliance.title": "الامتثال",
  "compliance.notYetChecked": "لم يُفحص بعد.",
  "compliance.retrievedClauses": "البنود المسترجعة",
  "compliance.reviewedBy": "روجعت بواسطة —",
  "compliance.unreviewed": "غير مراجَع",
  "compliance.pendingReview": "قيد المراجعة",
  "compliance.disclaimer":
    "كل بند وراء هذه الإجابة تمت صياغته بواسطة الذكاء الاصطناعي ولم تتم مراجعته من قِبل شريك قانوني مرخّص. اعتبر هذا نقطة انطلاق للتحقق اليدوي من هيئة التنظيم العقاري (RERA)، وليس استشارة قانونية.",

  "comps.comparableTransactions": "المعاملات المرجعية",
  "comps.noComps": "لم تُسترجع معاملات مرجعية بعد.",
  "comps.colTransaction": "المعاملة",
  "comps.colBuilding": "المبنى",
  "comps.colBeds": "الغرف",
  "comps.colPrice": "السعر",
  "comps.colPricePerSqft": "درهم/قدم²",
  "comps.colDate": "التاريخ",
  "comps.colSource": "المصدر",
  "comps.provenanceSynthetic": "بيانات تجريبية",
  "comps.provenanceDldKaggle": "دائرة الأراضي (عامة)",
  "comps.provenanceDldOpenFree": "دائرة الأراضي (رسمية)",
  "comps.provenanceLicensedPartner": "مرخّصة",

  "footer.tagline": "تحليل الصفقات العقارية بالذكاء الاصطناعي الوكيل لسوق دبي. كل ادعاء يوثّق مصدره.",
  "footer.product": "المنتج",
  "footer.pricing": "الأسعار",
  "footer.guides": "أدلة السوق",
  "footer.status": "حالة النظام",
  "footer.legal": "الشؤون القانونية",
  "footer.terms": "شروط الخدمة",
  "footer.privacy": "سياسة الخصوصية",
  "footer.dpa": "ملحق معالجة البيانات",
  "footer.contact": "تواصل معنا",
  "footer.contactSales": "تواصل مع المبيعات",
  "footer.dataNotice": "النسخة التجريبية تعمل على بيانات اصطناعية وبيانات مفتوحة عامة — راجع مصادر البيانات في وثائقنا.",
  "footer.rights": "جميع الحقوق محفوظة.",

  "pricing.eyebrow": "الأسعار",
  "pricing.title": "أسعار بسيطة وشفافة.",
  "pricing.subtitle": "ابدأ مجانًا مع بحث مقارنات غير محدود. قم بالترقية عند الحاجة لمزيد من استعلامات الصفقات الكاملة.",
  "pricing.getStarted": "ابدأ الآن",
  "pricing.contactSales": "تواصل مع المبيعات",
  "pricing.faqTitle": "أسئلة شائعة",

  "legal.draftBanner":
    "مسودة — قيد المراجعة القانونية. هذه الصفحة نموذج مبدئي، وليست وثيقة قانونية مُراجعة أو ملزمة. لا تعتمد عليها قبل موافقة المستشار القانوني.",
  "legal.lastUpdated": "آخر تحديث",

  "home.howItWorks": "كيف يعمل",
  "home.step1Title": "اسأل بلغة طبيعية",
  "home.step1Body": "«شقة غرفتي نوم في الخليج التجاري بأقل من ٢ مليون درهم» — بلا نماذج أو مرشحات معقدة.",
  "home.step2Title": "الوكلاء يجلبون المقارنات ويقيّمون",
  "home.step2Body": "معاملات مرجعية حقيقية، نموذج إحصائي، ونطاق تقييم قابل للدفاع عنه.",
  "home.step3Title": "فحص الامتثال ومذكرة موثّقة",
  "home.step3Body": "بنود هيئة التنظيم العقاري مسترجعة وموثّقة، أو إفصاح صادق بـ«تعذّر التحقق» — لا تخمين أبدًا.",
  "home.pricingTeaser": "مجاني للبدء. بحث مقارنات غير محدود في كل باقة.",
  "home.viewPricing": "عرض الأسعار",
};

export const DICTIONARIES: Record<Locale, Dict> = { en, ar };

export function translate(locale: Locale, key: string): string {
  return DICTIONARIES[locale][key] ?? DICTIONARIES.en[key] ?? key;
}

export function dirFor(locale: Locale): "rtl" | "ltr" {
  return locale === "ar" ? "rtl" : "ltr";
}
