var ProgressSummaryView = function(type) {
    var fInitialized = false,
        template = Templates.get("profile.class-progress-summary"),
        exerciseStatusInfo = {
                struggling: {
                    display: "מתקשה",
                    fShowOnLeft: true,
                    order: 0},
                review: {
                    display: "לבחון מחדש",
                    fShowOnLeft: true,
                    order: 1},
                proficient: {
                    display: "מיומן",
                    fShowOnLeft: true,
                    order: 2},
                started: {
                    display: "התחיל",
                    fShowOnLeft: false,
                    order: 3},
                "not-started": {
                    display: "לא התחיל",
                    fShowOnLeft: false,
                    order: 4}
        },
        videoStatusInfo = {
            completed: {
                display: "סיים",
                fShowOnLeft: true,
                order: 0},
            started: {
                display: "התחיל",
                fShowOnLeft: false,
                order: 1},
            "not-started": {
                display: "לא התחיל",
                fShowOnLeft: false,
                order: 2}
        },
        updateFilterTimeout = null,
        context = null,
        statusInfo = null;
    if (type == "video") {
        statusInfo = videoStatusInfo;
    } else {
        statusInfo = exerciseStatusInfo;
    }

    function toPixelWidth(num) {
        return Math.round(200 * num / context.num_students);
    }

    function filterSummaryRows() {
        updateFilterTimeout = null;
        var filterText = $("#student-progresssummary-" + type + "-search").val()
                            .toLowerCase();
        $(".item-row").each(function(index) {
            var jel = $(this),
                exerciseName = jel.find(".item-name span")
                                .html().toLowerCase();
            if (filterText == "" || exerciseName.indexOf(filterText) > -1) {
                jel.show();
            } else {
                jel.hide();
            }
        });
    }

    function init() {
        fInitialized = true;

        // Register partials and helpers
        Handlebars.registerPartial("class-progress-column", Templates.get("profile.class-progress-column"));

        Handlebars.registerHelper("toPixelWidth", function(num) {
            return toPixelWidth(num);
        });

        Handlebars.registerHelper("toNumberOfStudents", function(num) {
            if (toPixelWidth(num) < 20) {
                return "";
            }
            return num;
        });

        Handlebars.registerHelper("toDisplay", function(status) {
            return (exerciseStatusInfo[status] || videoStatusInfo[status]).display;
        });

        Handlebars.registerHelper("progressColumn", function(block) {
            this.progressSide = block.hash.side === "left" ? "right" : "left";
            return block(this);
        });

        Handlebars.registerHelper("progressIter", function(progress, block) {
            var result = "",
                fOnLeft = (block.hash.side === "left");

            $.each(progress, function(index, p) {
                if (fOnLeft === (exerciseStatusInfo[p.status] || videoStatusInfo[p.status]).fShowOnLeft) {
                    result += block(p);
                }
            });

            return result;
        });

        // Delegate clicks to expand rows and load student graphs
        $("#graph-content").delegate(".item-row", "click", function(e) {
            var jRow = $(this),
                studentLists = jRow.find(".student-lists");

            if (studentLists.is(":visible")) {
                jRow.find(".segment").each(function(index) {
                    var jel = $(this),
                        width = jel.data("width"),
                        span = width < 20 ? "" : jel.data("num");
                    jel.animate({width: width}, 350, "easeInOutCubic")
                        .find("span").html(span);
                });

                studentLists.fadeOut(100, "easeInOutCubic");
            } else {
                jRow.find(".segment").animate({width: 100}, 450, "easeInOutCubic", function() {
                    var jel = $(this),
                        status = jel.data("status");
                    jel.find("span").html(status);
                });

                studentLists.delay(150).fadeIn(650, "easeInOutCubic");
            }
        });

        $("#stats-filters").delegate("#student-progresssummary-" + type + "-search", "keyup", function() {
            if (updateFilterTimeout == null) {
                updateFilterTimeout = setTimeout(filterSummaryRows, 250);
            }
        });

    }

    return {
        render: function(c) {
            context = c;
            if (!fInitialized) {
                init();
            }
            if (type == "video") {
                context.items = context.videos;
            } else {
                context.items = context.exercises;
            }

            $.each(context.items, function(index, item) {
                item.progress.sort(function(first, second) {
                    return statusInfo[first.status].order - statusInfo[second.status].order;
                });
            });
            $("#graph-content").html(template(context));
        }
    };
};
