/**
 * Out-of-the-box experience logic for the profile page.
 * Dependent on the contents of profile-package.
 */

if (typeof Profile !== "undefined") {
    Profile.showIntro_ = function() {
        if (Profile.profile.isPhantom()) {
            // For phantom users, don't show a tour flow, but a single dialog
            // with clear call-to-action to login.
            guiders.createGuider({
                buttons: [
                    {
                        onclick: doneGuiding,
                        text: "לא תודה",
                        classString: "simple-button action-gradient"
                    },
                    {
                        onclick: doneGuiding,
                        text: "מגניב - תן לי להתחבר!",
                        onclick: function() {
                            var postLoginUrl = "/postlogin?continue=" +
                                    encodeURIComponent(window.location.href);
                            window.location.href = "/login?continue=" +
                                    encodeURIComponent(postLoginUrl);
                        },
                        classString: "simple-button action-gradient green"
                    }
                ],
                title: "התחברו כדי לשמור ולהתאים את הפרופיל שלכם!",
                description: "עמוד הפרופיל מציג לכם את ההתקדמות הנפלאה שעשיתם באתר. אם תתחברו, תוכלו אפילו להתאים ולשתף את הפרופיל שלכם עם חבריכם!",
                overlay: true
            }).show();
            return;
        }

        var isFullyEditable = Profile.profile.get("isDataCollectible");

        var doneGuiding = function() {
            guiders.hideAll();
            if (isFullyEditable) {
                $("#edit-basic-info").click();
            }
        }

        guiders.createGuider({
            id: "welcome",
            next: "basic-profile",

            buttons: [
                {
                    onclick: doneGuiding,
                    text: "תודה!",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "מגניב - תנו לי סיור!",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "ברוכים הבאים לפרופיל החדש שלכם!",
            description: "בדף זה תוכלו לעדכן את הפרטים שלכם ולהתעדכן על הפעילות שלכם באקדמיית קהאן.", 
            overlay: true
        }).show();

        guiders.createGuider({
            id: "basic-profile",
            next: "display-case",

            attachTo: ".basic-user-info",
            highlight: ".basic-user-info",
            overlay: true,
            position: 3,
            buttons: [
                {
                    onclick: doneGuiding,
                    text: "סגור",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "אוקי, הלאה...",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "זה הכל אתם.",
            description: isFullyEditable ?
                "כאן תמצאו את המידע הבסיסי שלכם. תוכלו לשנות את שם המשתמש שלכם ולבחור תמונת פרופיל מגניבה על ידי לחיצה על התמונה הנוכחית." : 
                "כאן תמצאו את המידע הבסיסי שלכם. תוכלו לבחור תמונת פרופיל מגניבה על ידי לחיצה על התמונה הנוכחית."
        });

        guiders.createGuider({
            id: "display-case",
            next: "more-info",

            attachTo: ".display-case-cover",
            highlight: ".sticker-book",
            overlay: true,
            position: 6,
            buttons: [
                {
                    onclick: doneGuiding,
                    text: "סגור",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "עוד, תראו לי עוד!",
                    classString: "simple-button action-gradient green"
                }
            ],
            title: "הציגו את ההישגים שלכם.",
            description: "תוכלו לבחור עד חמש מדליות להציג בתיבת התצוגה הנוצצת שלכם!"
        });

        guiders.createGuider({
            id: "more-info",
            next: "privacy-settings",

            attachTo: ".vertical-tab-list",
            highlight: ".vertical-tab-list",
            overlay: true,
            position: 9,
            buttons: (isFullyEditable ?
                [{
                    onclick: doneGuiding,
                    text: "סגור",
                    classString: "simple-button action-gradient"
                },
                {
                    action: guiders.ButtonAction.NEXT,
                    text: "אחלה, יש עוד?",
                    classString: "simple-button action-gradient green"
                }] : [{
                    onclick: doneGuiding,
                    text: "סבבה! תנו לי לשחק עם העמוד!",
                    classString: "simple-button action-gradient green"
                }]
            ),
            title: "מה המצב?",
            description: "הסטטיסטיקות של פעילותכם באתר זמינות במרחק לחיצה בתפריט זה. אל דאגה, הנתונים חשופים רק לכם ולמדריכים שלכם, ולא לאף-אחד אחר."
        });

        if (isFullyEditable) {
            guiders.createGuider({
                id: "privacy-settings",

                attachTo: ".edit-visibility",
                highlight: ".user-info, .edit-visibility",
                overlay: true,
                position: 3,
                buttons: [{
                    onclick: doneGuiding,
                    text: "סבבה. עכשיו תנו לי לשוטט!",
                    classString: "simple-button action-gradient green"
                }],
                title: "שתף עם העולם! <span style='font-size:65%'>(אבל רק אם אתם רוצים)</span>",
                description: "ניתן להפוך את העמוד שלכם לציבורי. כך תקבלו איזור משלכם באקדמיית קהאן, ומשתמשים אחרים יוכלו לבקר בו. אל דאגה - תמיד תוכלו להפוך את הפרופיל שלכם בחזרה לפרטי, ואז רק אתם והמדריכים שלכם יוכלו לראות את הנתונים שלכם."
            });

            
        }
    }
}
