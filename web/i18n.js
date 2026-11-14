/* ClipDrop translations. English text is the key; add a language by adding a table.
   Static text on the page is translated automatically; code uses I18N.T("text", {vars}). */
(function () {
  "use strict";
  const AR = {
    // ---------- header, tabs, lists
    "Clips": "المقاطع", "Files": "الملفات", "Help": "المساعدة", "Settings": "الإعدادات",
    "Search clips": "ابحث في المقاطع", "Search files": "ابحث في الملفات", "Sort": "الترتيب",
    "Newest": "الأحدث", "Oldest": "الأقدم", "Longest": "الأطول", "Shortest": "الأقصر",
    "Biggest": "الأكبر حجمًا", "Smallest": "الأصغر حجمًا", "Name A–Z": "الاسم أ–ي", "By game": "حسب اللعبة",
    "Select": "تحديد", "All": "الكل", "★ Favorites": "★ المفضلة", "Favorite": "مفضلة",
    "★ Favorite": "★ للمفضلة", "Unfavorite": "إزالة من المفضلة", "Send to iPhone Photos": "إرسال لصور الآيفون",
    "Delete": "حذف", "Done": "تم", "Clip it": "احفظ مقطع", "Save": "حفظ", "Watch": "مشاهدة", "NEW CLIP": "مقطع جديد",
    "NEW": "جديد", "Other": "أخرى", "Close": "إغلاق", "Loading clips…": "جارٍ تحميل المقاطع…",
    "Recording now": "يسجّل الآن", "Waiting for a game": "بانتظار لعبة", "Recording off": "التسجيل متوقف", "Starting…": "يبدأ…",
    "{n} clips": "{n} مقطع", "{size} free": "{size} متاح", "{n} selected": "تم تحديد {n}",
    "just now": "الآن", "{n} min ago": "قبل {n} د", "{n} h ago": "قبل {n} س",
    "{m} min {s} s": "{m} د {s} ث", "{m} min": "{m} د", "{s} s": "{s} ث", "Last {len}": "آخر {len}",
    "No clips match.": "لا توجد مقاطع مطابقة.", "No clips yet.": "لا توجد مقاطع بعد.",
    "Press your hotkey on the PC ({key}) or tap Clip it to save the last moments of your game.":
      "اضغط اختصارك على الكمبيوتر ({key}) أو اضغط «احفظ مقطع» لحفظ آخر لحظات لعبتك.",
    "How it works": "طريقة العمل", "New clip saved": "تم حفظ مقطع جديد",
    "Select some first": "حدد شيئًا أولًا",
    "Delete {n} item(s)? This can't be undone.": "حذف {n}؟ لا يمكن التراجع عن هذا.",
    "{n} added to favorites": "أُضيف {n} للمفضلة", "{n} removed from favorites": "أُزيل {n} من المفضلة",
    "{n} deleted": "تم حذف {n}",
    "{n} will go to your iPhone Photos next time the shortcut runs": "سيصل {n} إلى صور الآيفون في المرة القادمة التي يعمل فيها الاختصار",
    "Your iPhone saves them next time the Get Clips shortcut runs": "يحفظها الآيفون في المرة القادمة التي يعمل فيها الاختصار",
    // ---------- player
    "Rename": "إعادة تسمية", "Edit": "تعديل", "Share size": "حجم للمشاركة", "Show in folder": "إظهار في المجلد",
    "Keep selection": "إبقاء الجزء المحدد", "Cut out selection": "قص الجزء المحدد",
    "Replace the original (no copy)": "استبدال الأصلي (بدون نسخة)", "Save edited copy": "حفظ نسخة معدّلة",
    "{t} kept": "يبقى {t}", "Game": "اللعبة", "Voice": "الصوت", "Volume": "مستوى الصوت",
    "Let the video load first": "انتظر حتى يتحمّل الفيديو", "Keep at least half a second": "أبقِ نصف ثانية على الأقل",
    "Replace the original clip? This can't be undone.": "استبدال المقطع الأصلي؟ لا يمكن التراجع عن هذا.",
    "Saving… (this can take a bit)": "جارٍ الحفظ… (قد يأخذ وقتًا)", "Saved: {name}": "تم الحفظ: {name}",
    "Making a small copy for sharing…": "جارٍ عمل نسخة صغيرة للمشاركة…",
    "Small copy ready (720p, H.264, plays everywhere).": "النسخة الصغيرة جاهزة (720p، H.264، تعمل في كل مكان).",
    "Save small copy": "حفظ النسخة الصغيرة", "Couldn't make it: {e}": "تعذّر عملها: {e}",
    "New name:": "الاسم الجديد:", "Renamed to {name}": "تمت إعادة التسمية إلى {name}",
    "Delete this clip? This can't be undone.": "حذف هذا المقطع؟ لا يمكن التراجع عن هذا.", "Deleted": "تم الحذف",
    // ---------- files
    "Send to phone": "إرسال للجوال", "Send to PC": "إرسال للكمبيوتر",
    "From PC": "من الكمبيوتر", "From {device}": "من {device}", "From phones": "من الجوالات", "phone": "الجوال", "PC": "الكمبيوتر",
    "No files match.": "لا توجد ملفات مطابقة.", "No shared files yet.": "لا توجد ملفات مشتركة بعد.",
    "Drag files into this window, or tap Send to phone. You can also right-click a file in Windows and pick Send to, then ClipDrop.":
      "اسحب الملفات إلى هذه النافذة أو اضغط «إرسال للجوال». تقدر أيضًا تضغط بالزر الأيمن على أي ملف في ويندوز وتختار «إرسال إلى» ثم ClipDrop.",
    "Tap Send to PC to send photos, videos or any file to your PC.": "اضغط «إرسال للكمبيوتر» لإرسال صور أو فيديوهات أو أي ملف إلى الكمبيوتر.",
    "Drop files to send to your phone": "أفلت الملفات لإرسالها لجوالك", "They show up in Files on your phone.": "تظهر في تبويب الملفات على جوالك.",
    "Drop files to send to your PC": "أفلت الملفات لإرسالها للكمبيوتر", "They show up in Files on your PC.": "تظهر في تبويب الملفات على الكمبيوتر.",
    "Sending {n} file(s)…": "جارٍ إرسال {n} ملف…", "All sent ✓": "تم إرسال الكل ✓", "Failed": "فشل",
    "Couldn't send {name}": "تعذّر إرسال {name}", "New file from {device}": "ملف جديد من {device}", "{n} new files": "{n} ملفات جديدة",
    "To put it in Photos: press and hold the picture, then tap Save to Photos.": "لحفظها في الصور: اضغط مطولًا على الصورة ثم اختر «حفظ في الصور».",
    "To put it in Photos: tap Save, open it from Downloads in the Files app, then Share and Save Video.":
      "لحفظه في الصور: اضغط «حفظ»، افتحه من التنزيلات في تطبيق الملفات، ثم مشاركة ← حفظ الفيديو.",
    "Delete this file from the PC? This can't be undone.": "حذف هذا الملف من الكمبيوتر؟ لا يمكن التراجع عن هذا.",
    // ---------- settings: frame
    "Search settings": "ابحث في الإعدادات", "No settings match.": "لا توجد إعدادات مطابقة.",
    "You have unsaved changes": "عندك تغييرات غير محفوظة", "Undo": "تراجع",
    "Reset this section to default": "إرجاع هذا القسم للوضع الافتراضي",
    "Back to default. Tap Save to keep it.": "رجع للافتراضي. اضغط «حفظ» لتثبيته.",
    "Settings saved": "تم حفظ الإعدادات", "Couldn't load settings": "تعذّر تحميل الإعدادات", "Saved": "تم الحفظ",
    "Close without saving your changes?": "إغلاق بدون حفظ التغييرات؟", "Copied": "تم النسخ",
    "Couldn't copy. Press and hold the link to copy it.": "تعذّر النسخ. اضغط مطولًا على الرابط لنسخه.",
    "ClipDrop {v}": "ClipDrop {v}", "Recording with {enc}": "يسجّل باستخدام {enc}",
    // categories
    "Recording": "التسجيل", "When and what to record": "متى وماذا يسجّل",
    "Video": "الفيديو", "Format, quality and smoothness": "الصيغة والجودة والسلاسة",
    "Hotkeys": "الاختصارات", "Keys that save clips": "أزرار حفظ المقاطع",
    "Sound": "الصوت", "Game sound and microphone": "صوت اللعبة والمايك",
    "Alerts": "التنبيهات", "Sounds and pop-ups": "الأصوات والرسائل المنبثقة",
    "Clips and games": "المقاطع والألعاب", "Folders and game detection": "المجلدات والتعرّف على الألعاب",
    "Files and sharing": "الملفات والمشاركة", "Sending files between PC and phone": "إرسال الملفات بين الكمبيوتر والجوال",
    "Phone": "الجوال", "Connect, auto-send, shortcuts": "الربط، الإرسال التلقائي، الاختصارات",
    "Language": "اللغة", "English or Arabic": "عربي أو إنجليزي",
    "App": "التطبيق", "Startup and info": "التشغيل والمعلومات",
    // recording
    "Recording on": "التسجيل يعمل", "Turn off to stop recording completely. Your clips stay.": "أطفئه لإيقاف التسجيل تمامًا. مقاطعك تبقى.",
    "When to record": "متى يسجّل", "Always": "دائمًا",
    "Records all the time, games or not. Good if you also want clips of videos, Discord calls or anything on your screen.":
      "يسجّل طوال الوقت، سواء فيه لعبة أو لا. مناسب إذا تبي مقاطع من فيديوهات أو مكالمات ديسكورد أو أي شيء على الشاشة.",
    "Only while I'm gaming": "فقط وقت اللعب",
    "Starts when a game opens and stops when you close it. Uses no graphics card or disk when you're not playing.":
      "يبدأ لما تفتح لعبة ويتوقف لما تقفلها. ما يستهلك كرت الشاشة أو القرص وأنت ما تلعب.",
    "Right now: {game} is open.": "الآن: {game} مفتوحة.",
    "What to record": "ماذا يسجّل", "Whole screen": "الشاشة كاملة",
    "Everything on your screen. Works with every game, but pop-ups like Discord messages end up in clips too.":
      "كل شيء على الشاشة. يعمل مع كل الألعاب، لكن الإشعارات مثل رسائل ديسكورد تظهر في المقاطع.",
    "Only the game window": "نافذة اللعبة فقط",
    "Just the game. When no game is open it records the whole screen instead.": "اللعبة فقط. إذا ما فيه لعبة مفتوحة يسجّل الشاشة كاملة.",
    "Screen": "الشاشة", "Which monitor to record if you have more than one.": "أي شاشة يسجّل إذا عندك أكثر من وحدة.",
    "Show the mouse": "إظهار الماوس", "Shows your mouse pointer in clips.": "يظهر مؤشر الماوس في المقاطع.",
    // video
    "Format": "الصيغة",
    "Works everywhere: every phone, WhatsApp, Discord, Instagram, video editors and old PCs. Biggest files. Pick this if you share clips a lot or aren't sure.":
      "يعمل في كل مكان: كل الجوالات، واتساب، ديسكورد، إنستقرام، برامج المونتاج والأجهزة القديمة. ملفاته الأكبر. اختره إذا تشارك كثير أو مو متأكد.",
    "Same quality at about half the size, so faster to send to your iPhone. Plays on iPhone, Mac and newer Android phones. Some Windows apps need the free \"HEVC Video Extensions\".":
      "نفس الجودة بنصف الحجم تقريبًا، فيوصل للآيفون أسرع. يعمل على الآيفون والماك وجوالات أندرويد الحديثة. بعض برامج ويندوز تحتاج إضافة «HEVC Video Extensions» المجانية.",
    "Smallest files. Needs a new graphics card (NVIDIA RTX 40, AMD RX 7000, Intel Arc or newer). Plays on iPhone 15 Pro and newer. Many apps can't open it yet.":
      "أصغر الملفات. يحتاج كرت شاشة حديث (NVIDIA RTX 40 أو AMD RX 7000 أو Intel Arc أو أحدث). يعمل على iPhone 15 Pro وأحدث. برامج كثيرة ما تفتحه بعد.",
    "All three are saved as .mp4 files.": "الصيغ الثلاث تنحفظ كملفات mp4.",
    "✓ your graphics card": "✓ كرت الشاشة", "✓ uses the processor": "✓ يستخدم المعالج", "not supported on this PC": "غير مدعوم في هذا الكمبيوتر",
    "Quality": "الجودة",
    "Good · 10 Mbps · about 40 MB per 30 s": "جيدة · 10 ميجابت · تقريبًا 40 ميجا لكل 30 ث",
    "High · 20 Mbps · about 75 MB per 30 s": "عالية · 20 ميجابت · تقريبًا 75 ميجا لكل 30 ث",
    "Very high · 40 Mbps · about 150 MB per 30 s": "عالية جدًا · 40 ميجابت · تقريبًا 150 ميجا لكل 30 ث",
    "Maximum · 70 Mbps · about 260 MB per 30 s": "أقصى جودة · 70 ميجابت · تقريبًا 260 ميجا لكل 30 ث",
    "Higher looks sharper in fast games but makes bigger files. HEVC and AV1 look as good as H.264 at about half this setting.":
      "الأعلى أوضح في الألعاب السريعة لكن الملفات أكبر. HEVC و AV1 تعطي نفس وضوح H.264 بنصف هذا الرقم تقريبًا.",
    "Frames per second": "الإطارات في الثانية",
    "30 · smallest files": "30 · أصغر الملفات", "60 · smooth (recommended)": "60 · سلس (موصى به)",
    "120 · very smooth, needs a strong PC": "120 · سلس جدًا، يحتاج جهاز قوي",
    "More frames make fast movement look smoother.": "إطارات أكثر تخلي الحركة السريعة أنعم.",
    "Video size": "مقاس الفيديو", "Same as my screen": "نفس مقاس شاشتي", "720p · smallest": "720p · الأصغر",
    "Smaller sizes make smaller files. \"Same as my screen\" keeps every detail.": "المقاسات الأصغر تعطي ملفات أصغر. «نفس مقاس شاشتي» يحافظ على كل التفاصيل.",
    "(custom)": "(مخصص)",
    // hotkeys
    "Each hotkey saves a different amount of the last moments. They work inside games. On PC, tap Press keys and press the combination you want.":
      "كل اختصار يحفظ مدة مختلفة من آخر اللحظات، ويشتغل داخل الألعاب. على الكمبيوتر اضغط «اضغط الأزرار» ثم اضغط التركيبة اللي تبيها.",
    "+ Add a hotkey": "+ إضافة اختصار", "Press keys": "اضغط الأزرار", "Press now…": "اضغط الآن…", "Remove": "إزالة",
    "Keep at least one hotkey": "خلّ اختصار واحد على الأقل",
    // sound
    "Record game sound": "تسجيل صوت اللعبة",
    "Records what you hear from this output. \"Windows default\" follows whatever you're using.": "يسجّل اللي تسمعه من هذا المخرج. «افتراضي ويندوز» يتبع اللي تستخدمه.",
    "Record my microphone": "تسجيل المايك",
    "Your voice is saved on its own track, so later you can turn it down or mute it in Edit.": "صوتك ينحفظ في مسار لحاله، فتقدر بعدين تخفضه أو تكتمه من «تعديل».",
    "Sound capture isn't installed. Run the ClipDrop setup again to fix it.": "تسجيل الصوت غير مثبت. شغّل برنامج تثبيت ClipDrop مرة ثانية لإصلاحه.",
    "Windows default": "افتراضي ويندوز", "(default)": "(الافتراضي)",
    // alerts
    "Play a sound when a clip is saved": "تشغيل صوت عند حفظ مقطع",
    "A short ding when it's saved, or a buzz if something went wrong.": "رنة قصيرة عند الحفظ، أو صوت تنبيه إذا صار خطأ.",
    "Show \"Clip saved\" in the game": "إظهار «تم حفظ المقطع» داخل اللعبة",
    "A small message in the top corner for 2 seconds. It never shows up in your clips. Works with borderless and windowed games. In exclusive fullscreen, Windows doesn't allow it, so you'll only hear the sound.":
      "رسالة صغيرة في الزاوية العلوية لمدة ثانيتين، وما تظهر في مقاطعك أبدًا. تعمل مع الألعاب بوضع نافذة أو بدون حدود. في وضع ملء الشاشة الحصري ويندوز ما يسمح بها، فبتسمع الصوت فقط.",
    "Tell me when files arrive on the PC": "نبّهني لما توصل ملفات للكمبيوتر",
    "A sound and a small pop-up on the PC when your phone sends files.": "صوت ورسالة صغيرة على الكمبيوتر لما يرسل جوالك ملفات.",
    // clips & games
    "Sort clips into game folders": "ترتيب المقاطع في مجلدات حسب اللعبة",
    "Clips are named after the game and saved in a folder for it.": "المقاطع تتسمى باسم اللعبة وتنحفظ في مجلد خاص فيها.",
    "Clips folder": "مجلد المقاطع", "Where new clips are saved on the PC. ~ means your user folder.": "مكان حفظ المقاطع الجديدة على الكمبيوتر. ~ تعني مجلد المستخدم.",
    "Always count these as games": "اعتبر هذي دائمًا ألعاب",
    "ClipDrop treats any program that fills the whole screen as a game. Add the program name of a game it misses, like one you play in a window. Separate names with commas.":
      "ClipDrop يعتبر أي برنامج يملأ الشاشة لعبة. أضف اسم برنامج اللعبة إذا ما تعرّف عليها، مثل لعبة تلعبها بنافذة. افصل الأسماء بفواصل.",
    "Never count these as games": "لا تعتبر هذي ألعاب أبدًا",
    "Fullscreen programs that aren't games, like video players. Browsers and Discord are already left out.": "برامج ملء الشاشة اللي مو ألعاب، مثل مشغلات الفيديو. المتصفحات وديسكورد مستثناة أصلًا.",
    // files & sharing
    "This device's name": "اسم هذا الجهاز",
    "Shown on files you send from this device, so you know where they came from. Only this device uses it.": "يظهر على الملفات اللي ترسلها من هذا الجهاز عشان تعرف مصدرها. يخص هذا الجهاز فقط.",
    "Folder for shared files": "مجلد الملفات المشتركة",
    "On the PC. Files from your phone go in a \"From (phone name)\" folder inside it, and files the PC sends go in \"From PC\".":
      "على الكمبيوتر. ملفات الجوال تروح لمجلد «From (اسم الجوال)» داخله، وملفات الكمبيوتر تروح لـ «From PC».",
    "Send PC photos and videos to iPhone Photos": "إرسال صور وفيديوهات الكمبيوتر إلى صور الآيفون",
    "If you set up auto-send, photos and videos you send from the PC go straight into your iPhone's Photos app. Other files wait in the Files tab.":
      "إذا فعّلت الإرسال التلقائي، الصور والفيديوهات اللي ترسلها من الكمبيوتر تنزل مباشرة في تطبيق الصور بالآيفون. باقي الملفات تنتظر في تبويب الملفات.",
    // phone
    "Your phone link": "رابط جوالك", "Copy": "نسخ",
    "Open it in Safari on your phone (same Wi-Fi). Keep it private.": "افتحه في Safari على جوالك (نفس الواي فاي). خلّه خاص.",
    "Auto-send to Photos": "الإرسال التلقائي للصور", "New clips go into your iPhone's Photos by themselves.": "المقاطع الجديدة تنزل في صور الآيفون تلقائيًا.",
    "Set up": "إعداد", "Open": "فتح",
    "\"Send to PC\" in the iPhone share menu": "«إرسال للكمبيوتر» في قائمة المشاركة بالآيفون",
    "Send photos and videos from the Photos app in full quality.": "أرسل الصور والفيديوهات من تطبيق الصور بجودتها الكاملة.",
    "Show the QR code": "إظهار رمز QR", "Scan it with your phone camera to connect.": "امسحه بكاميرا الجوال للربط.",
    // language & app
    "Automatic": "تلقائي", "Each device uses its own language.": "كل جهاز يستخدم لغته.",
    "Start with Windows": "التشغيل مع ويندوز", "ClipDrop starts quietly by the clock when you turn on your PC.": "ClipDrop يشتغل بهدوء جنب الساعة لما تشغّل الكمبيوتر.",
    "How to use ClipDrop": "طريقة استخدام ClipDrop", "Step-by-step guide for the PC and the phone.": "شرح خطوة بخطوة للكمبيوتر والجوال.",
    // ---------- updates
    "Updates": "التحديثات", "Keep ClipDrop up to date": "خلّ ClipDrop محدّث",
    "What's new": "وش الجديد", "Update now": "حدّث الآن", "Later": "لاحقًا", "Hide": "إخفاء", "Try again": "حاول مرة ثانية",
    "ClipDrop {v} is ready": "ClipDrop {v} جاهز", "ClipDrop is up to date": "ClipDrop محدّث",
    "You have {cur}. Download size {size}.": "عندك {cur}. حجم التنزيل {size}.",
    "You have the newest version ({cur}).": "عندك أحدث نسخة ({cur}).",
    "Downloading update… {p}%": "جارٍ تنزيل التحديث… {p}%", "Installing update…": "جارٍ تثبيت التحديث…",
    "Downloading… {p}%": "جارٍ التنزيل… {p}%",
    "Installing. ClipDrop closes and opens again in a moment. This page reloads by itself.": "جارٍ التثبيت. ClipDrop يقفل ويفتح مرة ثانية بعد لحظات، والصفحة تتحدث لحالها.",
    "Check now": "ابحث الآن", "See update": "عرض التحديث", "Checking…": "جارٍ البحث…",
    "Version {v} is ready to install.": "النسخة {v} جاهزة للتثبيت.", "You have the newest version.": "عندك أحدث نسخة.",
    "Check for updates automatically": "البحث عن تحديثات تلقائيًا",
    "When ClipDrop starts and once a day. You get a message when a new version is ready.": "عند تشغيل ClipDrop ومرة كل يوم. توصلك رسالة إذا فيه نسخة جديدة.",
    "Install updates automatically": "تثبيت التحديثات تلقائيًا",
    "Updates install by themselves, without asking. ClipDrop closes for a few seconds and opens again. Your settings, clips and files always stay.":
      "التحديثات تتثبت لحالها بدون ما تسألك. ClipDrop يقفل ثواني ويفتح مرة ثانية. إعداداتك ومقاطعك وملفاتك تبقى دائمًا.",
    "All versions and what changed": "كل النسخ ووش تغيّر", "Opens the ClipDrop page on GitHub.": "يفتح صفحة ClipDrop في GitHub.",
    "Couldn't check for updates. Are you online?": "تعذّر البحث عن تحديثات. هل أنت متصل بالإنترنت؟",
    "No update to install": "ما فيه تحديث للتثبيت",
    "The update has no fingerprint, so it wasn't installed.": "التحديث ما معه بصمة، فما تم تثبيته.",
    "The download didn't match its fingerprint, so it wasn't installed. Try again.": "الملف المنزّل ما طابق بصمته، فما تم تثبيته. حاول مرة ثانية.",
    "The update couldn't be downloaded. Check your internet and try again.": "تعذّر تنزيل التحديث. تأكد من الإنترنت وحاول مرة ثانية.",
    // ---------- server messages
    "Something went wrong": "صار خطأ",
    "Not recording right now: no game is open (Settings > When to record).": "ما يسجّل الآن: ما فيه لعبة مفتوحة (الإعدادات ← متى يسجّل).",
    "Nothing recorded yet. Wait a few seconds and try again.": "ما انسجّل شيء بعد. انتظر ثواني وحاول مرة ثانية.",
    "Recording is turned off in Settings.": "التسجيل مطفأ من الإعدادات.",
    "A hotkey needs a key, like ctrl+f9": "الاختصار يحتاج زر، مثل ctrl+f9",
    "Clip length must be between 5 seconds and 10 minutes": "طول المقطع لازم يكون بين 5 ثواني و10 دقائق",
    "Clip not found": "المقطع غير موجود", "File not found": "الملف غير موجود",
    "Frames per second must be between 10 and 240": "الإطارات لازم تكون بين 10 و240",
    "Name can't be empty": "الاسم ما يصير فاضي", "Quality must look like 20M": "الجودة لازم تكون مثل 20M",
    "The clip must be at least half a second long": "المقطع لازم يكون نصف ثانية على الأقل",
    "The upload stopped before the end. Try again.": "توقف الإرسال قبل ما يكمل. حاول مرة ثانية.",
    "Two hotkeys use the same keys": "فيه اختصارين بنفس الأزرار",
    "Hotkeys only work on Windows": "الاختصارات تعمل على ويندوز فقط", "not active": "غير مفعّل", "Not allowed": "غير مسموح",
  };
  const AR_PATTERNS = [
    [/^Unknown key: (.+)$/, "زر غير معروف: $1"],
    [/^(.+) is already used by another app\. Pick another one\.$/, "$1 مستخدم من برنامج ثاني. اختر غيره."],
  ];

  const lang = (window.CD_LANG === "ar" || window.CD_LANG === "en") ? window.CD_LANG
    : ((navigator.language || "").toLowerCase().startsWith("ar") ? "ar" : "en");

  function T(s, vars) {
    let r = s;
    if (lang === "ar") {
      if (AR[s] !== undefined) r = AR[s];
      else for (const [re, rep] of AR_PATTERNS) if (re.test(s)) { r = s.replace(re, rep); break; }
    }
    if (vars) r = r.replace(/\{(\w+)\}/g, (m, k) => (vars[k] !== undefined ? vars[k] : m));
    return r;
  }

  const ATTRS = ["placeholder", "title", "aria-label"];
  function tr(node) {
    if (node.nodeType === 3) {
      const raw = node.nodeValue, key = raw.replace(/\s+/g, " ").trim();
      if (key && AR[key] !== undefined) node.nodeValue = raw.replace(raw.trim(), AR[key]);
      return;
    }
    if (node.nodeType !== 1 || node.tagName === "SCRIPT" || node.tagName === "STYLE") return;
    for (const a of ATTRS) {
      const v = node.getAttribute && node.getAttribute(a);
      if (v && AR[v] !== undefined) node.setAttribute(a, AR[v]);
    }
    for (const c of node.childNodes) tr(c);
  }

  if (lang === "ar") {
    document.documentElement.lang = "ar";
    document.documentElement.dir = "rtl";
    const start = () => {
      tr(document.body);
      new MutationObserver(ms => {
        for (const m of ms) {
          if (m.type === "characterData") tr(m.target);
          else m.addedNodes.forEach(tr);
        }
      }).observe(document.body, { childList: true, subtree: true, characterData: true });
    };
    if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
  }
  window.I18N = { T, lang };
})();
