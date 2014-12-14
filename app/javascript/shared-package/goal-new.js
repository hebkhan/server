var GoalCreator = {
    objectives: [],
    videosAreInit: false,

    init: function() {
        $(window).resize($.proxy(this.resize, this));

        $("#create-goal .goal-title")
            .focus(function() { $(this).animate({width: "600px"});})
            .blur(function() { $(this).animate({width: "250px"});})
            .placeholder();

        var form = $("#create-goal");
        form.find("input").mouseup(function() { $(this).removeClass("fieldError"); });
        form.find('input[name="title"]')
            .change(function() { GoalCreator.updateViewAndDescription(); })
            .keypress(function(e) {
                if (e.which == "13") { // enter
                    e.preventDefault();
                    $(e.target).blur();
                }
            });

        GoalCreator.updateViewAndDescription();
    },
    getCurrentObjectives: function() {
        if ($(".create-goal-page").parent().data("target")) {
            // this goal is targeted at some other user,
            // so the current-objectives are of no use to us
            return {};
        }

        var list = {};
        $.each(GoalBook.models, function(idx, model) {
            $.each(model.get("objectives"), function(idx2, objective) {
                list[objective.internal_id] = true;
            });
        });
        return list;
    },

    initCatalog: function() {
        $("#goal-choose-videos")

            .on("click", ".vl", function(e) {
                // prevent the href navigation from occuring
                e.preventDefault();

                var jel = $(e.currentTarget);
                var href = jel.attr("href");
                if (typeof href === "undefined") {
                    return;
                }

                var type = href.indexOf("/video")==0 ? "video" : "exercise";
                var span = jel.children("span");
                var name = jel.attr("data-id");
                var title = span.text();
                GoalCreator.onClicked(name, title, type);
            });

        $("#goal-choose-videos .vl").each(function(i, element) {
            var jel = $(element);
            var span = jel.children("span");
            var image = $(span).css("background-image");

            if (image.indexOf("indicator-complete") >= 0) {
                jel.addClass("goalVideoInvalid");
                jel.removeAttr("href");
            }
        });
    },

    // reset window state
    reset: function() {
        GoalCreator.objectives = [];
        $('#create-goal input[name="title"]').val("");

        GoalCreator.updateCount();
        GoalCreator.updateViewAndDescription();
        GoalCreator.showCatalog();
    },

    toggleObjectiveInternal: function(type, css, id, name) {
        var idx = 1;
        var found_index = -1;

        $("#goal-commit-response").hide();

        $.each(GoalCreator.objectives, function(index, objective) {
            if (objective.type == type && objective.id == id) {
                found_index = index;
            }

            if (objective.idx >= idx)
                idx = objective.idx + 1;
        });

        if (found_index >= 0) {
            // Remove objective
            var objective = GoalCreator.objectives[found_index];
            GoalCreator.objectives.splice(found_index, 1);
            return null;
        } else if (GoalCreator.objectives.length < 10) {
            var newObjective = {
                type: type,
                css: css,
                description: name,
                progress: 0,
                url: "javascript:GoalCreator.onSelectedObjectiveClicked('" +
                    type + "', '" + css + "', '" + id + "', '" + name + "');",

                idx: idx,
                id: id
            };

            GoalCreator.objectives.push(newObjective);
            return newObjective;
        }
    },
    updateViewAndDescription: function() {
        var goalObject = {
            title: $("#create-goal").find('input[name="title"]').val(),
            objectives: GoalCreator.objectives
        };

        var view = Templates.get("shared.goal-create")(goalObject);
        $("#create-goal-view").html(view);

        if (GoalCreator.objectives.length < 2) {
            $("#create-goal-view .goal").addClass("with-border");
        } else {
            $("#create-goal-view .goal").removeClass("with-border");
        }

        if (GoalCreator.objectives.length === 0) {
            $("#goal-info-section > .goal-description").remove();
        }
        if (GoalCreator.objectives.length > 0 && $("#goal-info-section").children(".goal-description").length === 0) {
            $("#create-goal-view .goal .goal-description").remove().insertAfter("#create-goal-view");
        }
        if (GoalCreator.objectives.length >= 1) {
            $("#create-goal-view .goal .goal-description").remove();
        }
        if (GoalCreator.objectives.length > 1) {
            $("#create-goal-view .goal li.objective").css("width", 100 / GoalCreator.objectives.length + "%");
            $("#create-goal-view .goal li.objective").last().children("a").css("border-right", "none");
        }

        var message = "";
        if (GoalCreator.objectives.length === 0) {
            message = "טרם בחרתם מטרות ליעד זה. בחרו <b>עד 10</b> תרגילים או סרטונים למטה.";
        } else {
            var matchingObjectives;

            message = "בכדי להשלים יעד זה, עליכם <ul>";

            // Exercises
            matchingObjectives = [];
            var hadExercises = false;
            $.each(GoalCreator.objectives, function(idx, objective) {
                if (objective.type == "GoalObjectiveExerciseProficiency")
                    matchingObjectives.push(objective);
            });
            if (matchingObjectives.length > 0) {
                hadExercises = true;
                message += "<li class='exercise-objectives'>להשיג מיומנות בתרגיל";
                if (matchingObjectives.length == 1) {
                    message += " <em>" + matchingObjectives[0].description + "</em>";
                } else {
                    message += "ים ";
                    $.each(matchingObjectives, function(idx, objective) {
                        if (idx === 0)
                            message += "<em>" + objective.description + "</em>";
                        else if (idx < matchingObjectives.length - 1)
                            message += ", <em>" + objective.description + "</em>";
                        else
                            message += " ו<em>" + objective.description + "</em>";
                    });
                }
                message += "</li>";
            }

            // Videos
            matchingObjectives = [];
            $.each(GoalCreator.objectives, function(idx, objective) {
                if (objective.type == "GoalObjectiveWatchVideo")
                    matchingObjectives.push(objective);
            });
            if (matchingObjectives.length > 0) {
                if (hadExercises) {
                    message += ", ו"
                }
                message += "<li class='video-ojectives'>לצפות בסרט";
                if (matchingObjectives.length == 1) {
                    message += " <em>" + matchingObjectives[0].description + "</em>";
                } else {
                    message += "ים ";
                    $.each(matchingObjectives, function(idx, objective) {
                        if (idx === 0)
                            message += "<em>" + objective.description + "</em>";
                        else if (idx < matchingObjectives.length - 1)
                            message += ", <em>" + objective.description + "</em>";
                        else
                            message += " ו<em>" + objective.description + "</em>";
                    });
                }
                message += ".</li>";
            }

            message += "</ul>";
        }
        $(".create-goal-page .goal-description").html(message);

        this.resize();
    },

    resize: function() {
        var content = $("#goal-choose-videos .dashboard-content-stretch");

        var container = $(".goal-new-custom.modal");
        var containerHeight = container.outerHeight(true);
        var yTopPadding = content.offset().top - container.offset().top;
        var yBottomPadding = 30; // magic numbers ahoy
        var newHeight = containerHeight - (yTopPadding + yBottomPadding);

        content.height(newHeight);
    },

    onClicked: function(id, title, type) {
        if (id in GoalCreator.getCurrentObjectives())
            return;  // Cannot select videos that are objectives in current goals

        if (type === "exercise") {
            GoalCreator.toggleObjectiveInternal("GoalObjectiveExerciseProficiency", "exercise", id, title);
        } else {
            GoalCreator.toggleObjectiveInternal("GoalObjectiveWatchVideo", "video", id, title);
        }

        GoalCreator.updateCount();
        GoalCreator.updateViewAndDescription();
    },

    showCatalog: function() {
        if (!GoalCreator.videosAreInit) {
            GoalCreator.videosAreInit = true;
            GoalCreator.initCatalog();
        }
        $("#goal-choose-videos").show();

        this.resize();

        for (var readableId in GoalCreator.getCurrentObjectives()) {
            $('.vl[data-id="' + readableId + '"]')
                .addClass("goalVideoInvalid")
                .removeAttr("href");
        }
    },
    updateCount: function() {
        var count = 0;

        $.each(GoalCreator.objectives, function(index, objective) {
            if (objective.type == "GoalObjectiveWatchVideo")
                count++;
        });

        $("#goal-video-count").html(count);

        $.each(GoalCreator.objectives, function(index, objective) {
            if (objective.type == "GoalObjectiveExerciseProficiency")
                count++;
        });

        $("#goal-exercise-count").html(count);


        $("#library-content-main").find(".vl").each(function(index, element) {
            var obj_id = $(element).attr("data-id");
            var found = false;

            $.each(GoalCreator.objectives, function(index2, objective) {
                if (objective.id == obj_id)
                {
                    found = true;
                }
            });

            var goalIcon = $(element).children(".video-goal-icon");
            if (found)
            {
                if (goalIcon.length === 0)
                    $('<span class="video-goal-icon"><img src="/images/flag.png"></span>')
                        .insertBefore($(element).children("span")[0]);
            }
            else
            {
                goalIcon.detach();
            }
        });
    },

    onSelectedObjectiveClicked: function(type, css, name, id) {
        GoalCreator.toggleObjectiveInternal(type, css, name, id);
        GoalCreator.updateCount();
        GoalCreator.updateViewAndDescription();
    },

    validate: function(form) {
        var error = "";

        if (GoalCreator.objectives.length < 2)
        {
            error = "יש לבחור לפחות שתי משימות.";
        }

        if (error !== "") {
            $("#goal-commit-response").html(error).show();
            return false;
        }
        return true;
    },

    submit: function() {
        var form = $("#create-goal");
        var html = "";

        if (!GoalCreator.validate(form))
            return;

        var titleField = form.find('input[name="title"]');
        if (titleField.val() === "" || titleField.val() === titleField.attr("placeholder"))
        {
            var d = new Date();
            titleField.val("יעד מותאם אישית: " + d.getDate() + "/" + (d.getMonth()+1) + "/" + d.getFullYear());
        }

        var target = $(".create-goal-page").parent().data("target");

        var goal = new Goal({
            target: target,
            title: titleField.val(),
            objectives: _.map(GoalCreator.objectives, function(o) {
                var newObj = {
                    type: o.type,
                    internal_id: o.id,
                    description: o.description
                };
                newObj.url = Goal.objectiveUrl(newObj);
                return newObj;
            })
        });
        // if this goal is not targeted to another user/student-list
        if (!target) {
            GoalBook.add(goal);
        }
        goal.save()
            .success(function(jqXHR) {
                KAConsole.log("Goal creation succeeded");
                GoalCreator.trigger("created", jqXHR)
            })
            .fail(function(jqXHR) {
                KAConsole.log("Goal creation failed: " + jqXHR.responseText, goal);
                if (!target) {
                    GoalBook.remove(goal);
                }
            });

        newCustomGoalDialog.hide();
        GoalCreator.reset();

        return false;
    }
};

_.extend(GoalCreator, Backbone.Events);
