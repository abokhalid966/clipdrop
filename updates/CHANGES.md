# ClipDrop versions

## 5.7

**ClipDrop 5.7: smoother clips**
- Clips no longer drop frames while you play. The picture now stays on the graphics card from capture to the encoder, instead of being copied through the CPU every frame.
- If the fast capture fails once, ClipDrop no longer drops to the slow screen capture for good. It only switches after 3 failures in a row, and tries the fast one again after 5 minutes.
- Fixed a small hitch every 2 seconds in saved clips.
- If your microphone won't open, ClipDrop now tries simpler settings before giving up.

<div dir="rtl">

**ClipDrop 5.7: مقاطع أنعم**
- المقاطع ما عادت تفقد إطارات وأنت تلعب. الصورة الحين تبقى على كرت الشاشة من التصوير إلى الترميز، بدل ما تنتقل للمعالج مع كل إطار.
- إذا فشل التصوير السريع مرة، ClipDrop ما عاد ينتقل للتصوير البطيء على طول. ينتقل فقط بعد 3 محاولات فاشلة ورا بعض، ويرجع يجرب السريع بعد 5 دقايق.
- انحلت رجفة صغيرة كانت تصير كل ثانيتين في المقاطع المحفوظة.
- إذا ما اشتغل المايك، ClipDrop الحين يجرب إعدادات أبسط قبل ما يستسلم.

</div>

## 5.6

**ClipDrop 5.6: instant clip alert, softer sound**
- The moment you press the clip hotkey, you hear the sound and see "Saving clip..." in the game. When the file is ready, the same message changes to "Clip saved". Before, both came only after the clip was written, a few seconds later.
- The old sharp beep is gone. Pick a sound in Settings > Alerts: Soft click, Soft chime, or No sound. Tap Listen to hear it on the PC.
- If a clip can't be saved, you hear two low notes and the message turns red.

<div dir="rtl">

**ClipDrop 5.6: تنبيه فوري وصوت أخف**
- أول ما تضغط اختصار الحفظ، تسمع الصوت ويطلع لك «جارٍ حفظ المقطع...» داخل اللعبة. ولما يجهز الملف، نفس الرسالة تتغير إلى «تم حفظ المقطع». قبل كانوا يطلعون بعد ما ينكتب المقطع، بعد كم ثانية.
- راح الصوت الحاد القديم. اختر الصوت من الإعدادات > التنبيهات: نقرة خفيفة، رنة خفيفة، أو بدون صوت. اضغط «اسمع» عشان تسمعه على الكمبيوتر.
- إذا ما انحفظ المقطع، بتسمع نغمتين منخفضتين والرسالة تصير حمراء.

</div>

## 5.5

**ClipDrop 5.5: clearer updates**
- "See update" in Settings now opens the update window on top, where you can see it. Before, it opened behind Settings.
- While ClipDrop updates, a full-screen panel shows each step: downloading, installing, and starting the new version. It also shows up when an update installs by itself.
- When the update is done, the page reloads by itself and says "Updated to ClipDrop 5.5". In games you get a pop-up when the update starts and when it's done.
- If an update takes more than 3 minutes, you get a note telling you what to do.

<div dir="rtl">

**ClipDrop 5.5: تحديثات أوضح**
- «شوف التحديث» في الإعدادات صار يفتح نافذة التحديث فوق، تقدر تشوفها. قبل كانت تنفتح ورا الإعدادات.
- وقت التحديث تطلع شاشة كاملة توضح كل خطوة: التنزيل، التثبيت، وتشغيل النسخة الجديدة. وتطلع بعد لما التحديث يتثبت لحاله.
- لما يخلص التحديث، الصفحة تتحدث لحالها وتقول «تم التحديث إلى ClipDrop 5.5». وداخل اللعبة يطلع لك تنبيه لما يبدأ التحديث ولما يخلص.
- لو التحديث طوّل أكثر من 3 دقايق، يطلع لك تنبيه يقول لك وش تسوي.

</div>

## 5.4

**ClipDrop 5.4: fixes "sample rate not set" when saving a clip**
- If ClipDrop closed the wrong way (crash, Task Manager, sign-out), its recorder could keep running on its own and record video with no sound. Clips then failed with "sample rate not set". Now the recorder always closes together with ClipDrop, and ClipDrop stops any old recorder it finds when it starts.
- Every recording uses its own buffer folder, so old pieces can't get mixed into a new clip.
- If the sound or the video stops coming in, ClipDrop restarts the recording by itself.
- If a clip has no sound in it, it's still saved (without sound) instead of failing.
- The log now shows the real reason when the microphone can't be used.

<div dir="rtl">

**ClipDrop 5.4: إصلاح خطأ «sample rate not set» عند حفظ المقطع**
- لو انقفل ClipDrop بطريقة غلط (تعليق، إدارة المهام، تسجيل خروج)، كان المسجل يكمل لحاله ويسجل فيديو بدون صوت، والمقاطع تفشل بخطأ «sample rate not set». الحين المسجل ينقفل دايم مع ClipDrop، وClipDrop يوقف أي مسجل قديم يلقاه أول ما يشتغل.
- كل تسجيل له مجلد خاص، فما تختلط قطع قديمة بمقطع جديد.
- لو وقف الصوت أو الفيديو، ClipDrop يعيد التسجيل من نفسه.
- لو المقطع ما فيه صوت، ينحفظ بدون صوت بدل ما يفشل.
- السجل يوضح السبب الحقيقي لو المايك ما اشتغل.

</div>

## 5.3

**ClipDrop 5.3: a new look**
- The whole app has a new design: warm black with one orange accent, cleaner lists and sharper buttons. Same buttons in the same places, so nothing to relearn.
- The emoji are gone. Icons are simple line icons now.
- New fonts (IBM Plex) for English and Arabic. They come with ClipDrop, so they work without internet.
- On the phone, your newest clip is shown big and older clips are listed under it in a compact list.
- The bottom button now says exactly what it does, like **Save last 30 s**, and on the PC it shows your hotkey.
- Filters show how many clips or files each one has.
- New orange app icon, also in the tray and the "Clip saved" pop-up in games.

<div dir="rtl">

**ClipDrop 5.3: شكل جديد**
- التطبيق كله بتصميم جديد: أسود دافئ مع لون برتقالي واحد، قوائم أنظف وأزرار أوضح. نفس الأزرار في نفس أماكنها، ما تحتاج تتعلم شي من جديد.
- شلنا الإيموجي. الأيقونات صارت خطوط بسيطة.
- خطوط جديدة (IBM Plex) للعربي والإنجليزي. تجي مع ClipDrop، فتشتغل بدون إنترنت.
- في الجوال، آخر مقطع يطلع كبير والمقاطع الأقدم تحته في قائمة مرتبة.
- الزر اللي تحت صار يقول وش يسوي بالضبط، مثل **احفظ آخر 30 ث**، وفي الكمبيوتر يوضح الاختصار.
- الفلاتر توضح كم مقطع أو ملف في كل وحدة.
- أيقونة برتقالية جديدة للتطبيق، وفي شريط المهام ورسالة «تم حفظ المقطع» داخل اللعبة.

</div>

## 5.2

**ClipDrop 5.2**
- **Fixed:** after changing a hotkey or its length, the hotkey could stop working and show "already used by another app", even though ClipDrop itself was holding it.
- If another app really is using your hotkey, ClipDrop now keeps trying and the hotkey starts working by itself as soon as the key is free.

<div dir="rtl">

**ClipDrop 5.2**
- **إصلاح:** بعد تغيير الاختصار أو مدته، كان الاختصار أحيانًا يوقف ويطلع «مستخدم من برنامج ثاني» مع إن ClipDrop نفسه هو اللي ماسكه.
- إذا كان فيه برنامج ثاني فعلًا يستخدم اختصارك، ClipDrop يحاول مرة ثانية تلقائيًا ويشتغل الاختصار أول ما يفضى.

</div>

## 5.1

**ClipDrop 5.1**
- **Automatic updates.** ClipDrop now checks for new versions and updates itself with one tap. Your settings, clips and files stay.
- New **Updates** section in Settings: check now, check automatically, or install automatically.
- "Check for updates" in the tray menu.
- Safety: every update is checked against its SHA-256 fingerprint before it installs.

Also in 5.0: file sharing between PC and phone, Arabic, and the new Settings page.

<div dir="rtl">

**ClipDrop 5.1**
- **تحديثات تلقائية.** ClipDrop صار يبحث عن النسخ الجديدة ويحدّث نفسه بضغطة وحدة. إعداداتك ومقاطعك وملفاتك تبقى.
- قسم **التحديثات** الجديد في الإعدادات: ابحث الآن، أو البحث التلقائي، أو التثبيت التلقائي.
- «البحث عن تحديثات» في قائمة الأيقونة جنب الساعة.
- أمان: كل تحديث يتأكد من بصمته (SHA-256) قبل التثبيت.

وفي 5.0: مشاركة الملفات بين الكمبيوتر والجوال، العربي، وصفحة الإعدادات الجديدة.

</div>
