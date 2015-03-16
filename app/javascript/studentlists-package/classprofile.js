/**
 * Code to handle the logic for the class profile page.
 */
// TODO: clean up all event listeners. This page does not remove any
// event listeners when tearing down the graphs.

var ClassProfile = {
    version: 0,
    initialGraphUrl: null, // Filled in by the template after script load.
    fLoadingGraph: false,
    fLoadedGraph: false,
    statusInfo: {
        video: {
            "watched-some":  "צפה חלקית",
            "watched-most":  "כמעט סיים",
            completed:  "סיים",
            started:  "התחיל",
            "not-started":  "לא התחיל",
        },
        exercise: {
            struggling:  "מתקשה",
            review:  "סיים",
            proficient:  "מיומן",
            started:  "התחיל",
            "not-started":  "לא התחיל",
        }
    },

    init: function() {

        $(".share-link").hide();
        $(".sharepop").hide();

        $(".achievement,.exercise,.video").hover(
            function () {
                $(this).find(".share-link").show();
                },
            function () {
                $(this).find(".share-link").hide();
                $(this).find(".sharepop").hide();
              });

        $(".share-link").click(function() {
            if ( $.browser.msie && (parseInt($.browser.version, 10) < 8) ) {
                $(this).next(".sharepop").toggle();
            } else {
                $(this).next(".sharepop").toggle(
                        "drop", { direction:"up" }, "fast" );
            }
            return false;
        });

        // Init Highcharts global options.
        Highcharts.setOptions({
            credits: {
                enabled: false
            },
            title: {
                text: ""
            },
            subtitle: {
                text: ""
            }
        });

        if ($.address){

            // this is hackish, but it prevents the change event from being fired twice on load
            if ( $.address.value() === "/" ){
                window.location = window.location + "#" + $(".graph-link:eq(0)").attr("href");
            }

            $.address.change(function( evt ){

                if ( $.address.path() !== "/"){
                    ClassProfile.historyChange( evt );
                }

            });

        }

        $(".graph-link").click(
            function(evt){
                evt.preventDefault();
                if($.address){
                    // only visit the resource described by the url, leave the params unchanged
                    var href = $( this ).attr( "href" )
                    var path = href.split("?")[0];

                    // visiting a different resource
                    if ( path !== $.address.path() ){
                        $.address.path( path );
                    }

                    // applying filters for same resource via querystring
                    else{
                        // make a dict of current qs params and merge with the link's
                        var currentParams = {};
                        _.map( $.address.parameterNames(), function(e){ currentParams[e] = $.address.parameter( e ); } );
                        var linkParams = ClassProfile.parseQueryString( href );
                        $.extend( currentParams, linkParams );

                        $.address.queryString( ClassProfile.reconstructQueryString( currentParams ) );
                    }
                }
            }
        );

        $("#individual_report #achievements #achievement-list > ul").delegate("li", "click", function(e) {
            var category = $(this).attr("id");
            var clickedBadge = $(this);

            $("#badge-container").css("display", "");
            clickedBadge.siblings().removeClass("selected");

            if ($("#badge-container > #" + category ).is(":visible")) {
               if (clickedBadge.parents().hasClass("standard-view")) {
                   $("#badge-container > #" + category ).slideUp(300, function(){
                           $("#badge-container").css("display", "none");
                           clickedBadge.removeClass("selected");
                       });
               }
               else {
                   $("#badge-container > #" + category ).hide();
                   $("#badge-container").css("display", "none");
                   clickedBadge.removeClass("selected");
               }
            }
            else {
               var jelContainer = $("#badge-container");
               var oldHeight = jelContainer.height();
               $(jelContainer).children().hide();
               if (clickedBadge.parents().hasClass("standard-view")) {
                   $(jelContainer).css("min-height", oldHeight);
                   $("#" + category, jelContainer).slideDown(300, function() {
                       $(jelContainer).animate({"min-height": 0}, 200);
                   });
               } else {
                   $("#" + category, jelContainer).show();
               }
               clickedBadge.addClass("selected");
            }
        });

        // remove goals from IE<=8
        $(".lte8 .goals-accordion-content").remove();

        $("#stats-nav #nav-accordion")
            .accordion({
                header:".header",
                active:".graph-link-selected",
                autoHeight: false,
                clearStyle: true
            });

        setTimeout(function(){
            if (!ClassProfile.fLoadingGraph && !ClassProfile.fLoadedGraph)
            {
                // If 1000 millis after document.ready fires we still haven't
                // started loading a graph, load manually.
                // The externalChange trigger may have fired before we hooked
                // up a listener.
                ClassProfile.historyChange();
            }
        }, 1000);

        ClassProfile.ExerciseProgressSummaryView = new ProgressSummaryView('exercise');
        ClassProfile.VideoProgressSummaryView = new ProgressSummaryView('video');

        $('#studentlists_dropdown').css('display', 'inline-block');
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length > 0) {
            var menu = $dropdown.menu();

            // Set the width explicitly before positioning it absolutely to satisfy IE7.
            menu.width(menu.width()).hide().css('position', 'absolute');

            menu.bind("menuselect", this.updateStudentList);

            $(document).bind("click focusin", function(e){
                if ($(e.target).closest("#studentlists_dropdown").length == 0) {
                    menu.hide();
                }
            });

            var button = $('#studentlists_dropdown > a').button({
                icons: {
                    secondary: 'ui-icon-triangle-1-s'
                }
            }).show().click(function(e){
                if (menu.css('display') == 'none')
                    menu.show().menu("activate", e, $('#studentlists_dropdown li[data-selected=selected]')).focus();
                else
                    menu.hide();
                e.preventDefault();
            });

            // get initially selected list
            var list_id = $.address.parameter("list_id");
            if (list_id) {
                $dropdown.children('li[data-selected=selected]').removeAttr("data-selected");
                $dropdown.children('li[data-list_id='+list_id+']').attr("data-selected", "selected");
            } else {
                list_id = $dropdown.children('li[data-selected=selected]').data('list_id');
            }
            var student_list = ClassProfile.getStudentListFromId(list_id);
            $dropdown.data('selected', student_list);
            $('#studentlists_dropdown .ui-button-text').text(student_list.name);

        }

        GoalCreator.bind("created", function(xhr) {
            ClassProfile.historyChange()
        })

    },

    highlightPoints: function(chart, fxnHighlight) {

        if (!chart) return;

        for (var ix = 0; ix < chart.series.length; ix++) {
            var series = chart.series[ix];

            this.muteSeriesStyles(series);

            for (var ixData = 0; ixData < series.data.length; ixData++) {
                var pointOptions = series.data[ixData].options;
                if (!pointOptions.marker) pointOptions.marker = {};
                pointOptions.marker.enabled = fxnHighlight(pointOptions);
                if (pointOptions.marker.enabled) {
                    pointOptions.marker.radius = 6;
                }
                series.data[ixData].update(pointOptions);
            }

            series.isDirty = true;
        }

        chart.redraw();
    },

    muteSeriesStyles: function(series) {
        if (series.options.fMuted) return;

        series.graph.attr('opacity', 0.1);
        series.graph.attr('stroke', '#CCCCCC');
        series.options.lineWidth = 1;
        series.options.shadow = false;
        series.options.fMuted = true;
    },

    accentuateSeriesStyles: function(series) {
        series.options.lineWidth = 3.5;
        series.options.shadow = true;
        series.options.fMuted = false;
    },

    highlightSeries: function(chart, seriesHighlight) {

        if (!chart || !seriesHighlight) return;

        for (var ix = 0; ix < chart.series.length; ix++)
        {
            var series = chart.series[ix];
            var fSelected = (series == seriesHighlight);

            if (series.fSelectedLast == null || series.fSelectedLast != fSelected)
            {
                if (fSelected)
                    this.accentuateSeriesStyles(series);
                else
                    this.muteSeriesStyles(series);

                for (var ixData = 0; ixData < series.data.length; ixData++) {
                    series.data[ixData].options.marker = {
                        enabled: fSelected,
                        radius: fSelected ? 5 : 4
                    };
                }

                series.isDirty = true;
                series.fSelectedLast = fSelected;
            }
        }

        var options = seriesHighlight.options;
        options.color = '#0080C9';
        seriesHighlight.remove(false);
        chart.addSeries(options, false, false);

        chart.redraw();
    },

    collapseAccordion: function() {
        // Turn on collapsing, collapse everything, and turn off collapsing
        $("#stats-nav #nav-accordion").accordion(
                "option", "collapsible", true).accordion(
                    "activate", false).accordion(
                        "option", "collapsible", false);
    },

    baseGraphHref: function(href) {
        // regex for matching scheme:// part of uri
        // see http://tools.ietf.org/html/rfc3986#section-3.1
        var reScheme = /^\w[\w\d+-.]*:\/\//;
        var match = href.match(reScheme);
        if (match) {
            href = href.substring(match[0].length);
        }

        var ixSlash = href.indexOf("/");
        if (ixSlash > -1)
            href = href.substring(href.indexOf("/"));

        var ixQuestionMark = href.indexOf("?");
        if (ixQuestionMark > -1)
            href = href.substring(0, ixQuestionMark);

        return href;
    },

    /**
    * Expands the navigation accordion according to the link specified.
    * @return {boolean} whether or not a link was found to be a valid link.
    */
    expandAccordionForHref: function(href) {
        if (!href) {
            return false;
        }

        href = this.baseGraphHref(href).replace(/[<>']/g, "");

        href = href.replace(/[<>']/g, "");
        var selectorAccordionSection =
                ".graph-link-header[href*='" + href + "']";

        if ( $(selectorAccordionSection).length ) {
            $("#stats-nav #nav-accordion").accordion(
                "activate", selectorAccordionSection);
            return true;
        }
        this.collapseAccordion();
        return false;
    },

    styleSublinkFromHref: function(href) {

        if (!href) return;

        var reDtStart = /dt_start=[^&]+/;

        var matchStart = href.match(reDtStart);
        var sDtStart = matchStart ? matchStart[0] : "dt_start=lastweek";

        href = href.replace(/[<>']/g, "");

        $(".graph-sub-link").removeClass("graph-sub-link-selected");
        $(".graph-sub-link[href*='" + this.baseGraphHref(href) + "'][href*='" + sDtStart + "']")
            .addClass("graph-sub-link-selected");
    },

    // called whenever user clicks graph type accordion
    loadGraphFromLink: function(el) {
        if (!el) return;
        ClassProfile.loadGraphStudentListAware(el.href);
    },

    loadGraphStudentListAware: function(url) {
        var $dropdown = $('#studentlists_dropdown ol');
        if ($dropdown.length == 1) {
            var list_id = $dropdown.data('selected').key;
            var qs = this.parseQueryString(url);
            qs['list_id'] = list_id;
            qs['version'] = ClassProfile.version;
            qs['dt'] = $("#targetDatepicker").val();
            url = this.baseGraphHref(url) + '?' + this.reconstructQueryString(qs);
        }

        this.loadGraph(url);
    },

    loadFilters : function( href ){
        // fix the hrefs for each filter
        var a = $("#stats-filters a[href^=\"" + href + "\"]").parent();
        $("#stats-filters .filter:visible").not(a).slideUp("slow");
        a.slideDown();
    },

    loadGraph: function(href, fNoHistoryEntry) {
        var apiCallbacksTable = {
            '/api/v1/user/students/goals': this.renderStudentGoals,
            '/api/v1/user/students/progressreport': ClassProfile.renderStudentProgressReport,
            '/api/v1/user/students/progress/exercise_summary': this.ExerciseProgressSummaryView.render,
            '/api/v1/user/students/progress/video_summary': this.VideoProgressSummaryView.render
        };
        if (!href) return;

        if (this.fLoadingGraph) {
            setTimeout(function(){ClassProfile.loadGraph(href);}, 200);
            return;
        }

        this.styleSublinkFromHref(href);
        this.fLoadingGraph = true;
        this.fLoadedGraph = true;

        var apiCallback = null;
        for (var uri in apiCallbacksTable) {
            if (href.indexOf(uri) > -1) {
                apiCallback = apiCallbacksTable[uri];
            }
        }
        $.ajax({
            type: "GET",
            url: Timezone.append_tz_offset_query_param(href),
            data: {},
            dataType: apiCallback ? 'json' : 'html',
            success: function(data){
                ClassProfile.finishLoadGraph(data, href, fNoHistoryEntry, apiCallback);
            },
            error: function() {
                ClassProfile.finishLoadGraphError();
            }
        });
        $("#graph-content").html("");
        this.showGraphThrobber(true);
    },
    renderStudentGoals: function(data, href) {
        var studentGoalsViewModel = {
            rowData: [],
            sortDesc: '',
            filterDesc: '',
            colors: "goals-class"
        };

        $.each(data, function(idx1, student) {
            student.goal_count = 0;
            student.most_recent_update = null;
            student.profile_url = student.profile_root + "/goals";

            if (student.goals != undefined && student.goals.length > 0) {
                $.each(student.goals, function(idx2, goal) {
                    // Sort objectives by status
                    var progress_count = 0;
                    var found_struggling = false;

                    goal.objectiveWidth = 100/goal.objectives.length;
                    goal.objectives.sort(function(a,b) { return b.progress-a.progress; });

                    $.each(goal.objectives, function(idx3, objective) {
                        Goal.calcObjectiveDependents(objective, goal.objectiveWidth);

                        if (objective.status == 'proficient')
                            progress_count += 1000;
                        else if (objective.status == 'started' || objective.status == 'struggling')
                            progress_count += 1;

                        if (objective.status == 'struggling') {
                            found_struggling = true;
                            objective.struggling = true;
                        }
                        objective.statusCSS = objective.status ? objective.status : "not-started";
                        objective.objectiveID = idx3;
                        var base = student.profile_root + "/vital-statistics";
                        if (objective.type === "GoalObjectiveExerciseProficiency") {
                            objective.url = base + "/exercise-problems/" + objective.internal_id;
                        } else if (objective.type === "GoalObjectiveAnyExerciseProficiency") {
                            objective.url = base + "/exercise-progress";
                        } else {
                            objective.url = base + "/activity";
                        }
                    });

                    // normalize so completed goals sort correctly
                    if (goal.objectives.length) {
                        progress_count /= goal.objectives.length;
                    }

                    if (!student.most_recent_update || goal.updated > student.most_recent_update)
                        student.most_recent_update = goal;

                    student.goal_count++;
                    row = {
                        rowID: studentGoalsViewModel.rowData.length,
                        student: student,
                        goal: goal,
                        progress_count: progress_count,
                        goal_idx: student.goal_count,
                        struggling: found_struggling
                    };

                    $.each(goal.objectives, function(idx3, objective) {
                        objective.row = row;
                    });
                    studentGoalsViewModel.rowData.push(row);
                });
            } else {
                studentGoalsViewModel.rowData.push({
                    rowID: studentGoalsViewModel.rowData.length,
                    student: student,
                    goal: {objectives: []},
                    progress_count: -1,
                    goal_idx: 0,
                    struggling: false
                });
            }
        });

        var template = Templates.get( "profile.profile-class-goals" );
        $("#graph-content").html( template(studentGoalsViewModel) );

        $("#class-student-goal .goal-row").each(function() {
            var goalViewModel = studentGoalsViewModel.rowData[$(this).attr('data-id')];
            goalViewModel.rowElement = this;
            goalViewModel.countElement = $(this).find('.goal-count');
            goalViewModel.startTimeElement = $(this).find('.goal-start-time');
            goalViewModel.updateTimeElement = $(this).find('.goal-update-time');

            ClassProfile.AddObjectiveHover($(this));

            $(this).find("a.objective").each(function() {
                var goalObjective = goalViewModel.goal.objectives[$(this).attr('data-id')];
                goalObjective.blockElement = this;

                if (goalObjective.type == 'GoalObjectiveExerciseProficiency') {
                    $(this).click(function() {
                        // TODO: awkward turtle, replace with normal href action
                        window.location = goalViewModel.student.profile_root
                                            + "/vital-statistics/exercise-problems/"
                                            + goalObjective.internal_id;
                    });
                } else {
                    // Do something here for videos?
                }
            });
        });

        $("#student-goals-sort")
            .off("change.goalsfilter")
            .on("change.goalsfilter", function() {
                ClassProfile.sortStudentGoals(studentGoalsViewModel);
            });
        $("input.student-goals-filter-check")
            .off("change.goalsfilter")
            .on("change.goalsfilter", function() {
                ClassProfile.filterStudentGoals(studentGoalsViewModel);
            });
        $("#student-goals-search")
            .off("keyup.goalsfilter")
            .on("keyup.goalsfilter", function() {
                ClassProfile.filterStudentGoals(studentGoalsViewModel);
            });

        $(".new-goal")
            .addClass("disabled")
            .removeClass("green")
            .click(function(e) {
                e.preventDefault();
                var users_csv = $(".goal-check:checked")
                    .map(function(){return $(this).data("id");})
                    .toArray()
                    // unique elements
                    .filter(function(el, index, arr) { return index === arr.indexOf(el); })
                    .join();
                window.newCustomGoalDialog.show("students:"+users_csv);
            })

        $(".delete-goals")
            .addClass("disabled")
            .removeClass("orange")
            .click(function(e) {
                e.preventDefault();
                var goals = $(".goal-check:checked")
                        .closest(".student-name")
                        .find(".goal-remove")
                        .map(function(){ return {
                            id:($(this).data("id")),
                            email:$(this).closest(".goal-row").data("student")};
                        }).toArray();
                $.ajax({
                    type: "POST",
                    url: "/api/v1/student/goals",
                    dataType: "json",
                    contentType: "application/json",
                    data: JSON.stringify(goals),
                    success: (function(xhr) {
                        ClassProfile.historyChange();
                    })
                });
            })

        $(".new-goal").add("delete-goals")
            .bind("goal-check-changed", function() {
                if ($(".goal-check:checked").length) {
                    $(".goal-check-all").attr("checked", true);
                    // see if there are removable goals
                    if ($(".goal-check:checked").closest(".student-name").find(".goal-remove").length) {
                        $(".delete-goals").addClass("orange").removeClass("disabled");
                    }
                    $(".new-goal").addClass("green").removeClass("disabled");
                } else {
                    $(".goal-check-all").attr("checked", false);
                    $(".delete-goals").removeClass("orange").addClass("disabled");
                    $(".new-goal").removeClass("green").addClass("disabled");
                }
            });

        $(".goal-check-all").change(function() {
            $(".goal-check").attr("checked", this.checked);
            $(".new-goal").add("delete-goals").trigger("goal-check-changed");
        });

        $(".goal-check").change(function() {
            // var student = $(this).closest(".goal-row").data("student");
            // $(".goal-row[data-student='" + student + "'] .goal-check").attr("checked", this.checked);
            $(".new-goal").add("delete-goals").trigger("goal-check-changed");
        });

        $(".goal-remove").click(function(e) {
            e.preventDefault();
            var goal_id = $(this).data("id");
            var student_email = $(this).closest(".goal-row").data("student");
            $.ajax({
                type: "DELETE",
                url: "/api/v1/student/goals/" + goal_id + "?" + $.param({"email": student_email}),
                // dataType: "json",
                // contentType: "application/json",
                // data: JSON.stringify({"email": student_email}),
                success: (function(xhr) {
                    ClassProfile.historyChange();
                })
            });
        });
        ClassProfile.sortStudentGoals(studentGoalsViewModel);
        ClassProfile.filterStudentGoals(studentGoalsViewModel);
    },
    sortStudentGoals: function(studentGoalsViewModel) {
        var sort = $("#student-goals-sort").val();
        var show_updated = false;

        if (sort == 'name') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (b.student.nickname > a.student.nickname)
                    return -1;
                if (b.student.nickname < a.student.nickname)
                    return 1;
                return a.goal_idx-b.goal_idx;
            });

            studentGoalsViewModel.sortDesc = 'שם תלמיד';
            show_updated = false; // started

        } else if (sort == 'progress') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                return b.progress_count - a.progress_count;
            });

            studentGoalsViewModel.sortDesc = 'התקדמות ליעד';
            show_updated = true; // updated

        } else if (sort == 'created') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.created > a.goal.created)
                        return 1;
                    if (b.goal.created < a.goal.created)
                        return -1;
                }
                return 0;
            });

            studentGoalsViewModel.sortDesc = 'מועד יצרית היעד';
            show_updated = false; // started

        } else if (sort == 'updated') {
            studentGoalsViewModel.rowData.sort(function(a,b) {
                if (a.goal && !b.goal)
                    return -1;
                if (b.goal && !a.goal)
                    return 1;
                if (a.goal && b.goal) {
                    if (b.goal.updated > a.goal.updated)
                        return 1;
                    if (b.goal.updated < a.goal.updated)
                        return -1;
                }
                return 0;
            });

            studentGoalsViewModel.sortDesc = 'מועד פעילות אחרון';
            show_updated = true; // updated
        }

        var container = $('#class-student-goal').detach();
        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            $(row.rowElement).detach();
            $(row.rowElement).appendTo(container);
            if (show_updated) {
                row.startTimeElement.hide();
                row.updateTimeElement.show();
            } else {
                row.startTimeElement.show();
                row.updateTimeElement.hide();
            }
        });
        container.insertAfter('#class-goal-filter-desc');

        ClassProfile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    updateStudentGoalsFilterText: function(studentGoalsViewModel) {
        var text = 'ממוין לפי ' + studentGoalsViewModel.sortDesc + '. ' + studentGoalsViewModel.filterDesc + '.';
        $('#class-goal-filter-desc').html(text);
    },
    filterStudentGoals: function(studentGoalsViewModel) {
        var filter_text = $.trim($("#student-goals-search").val().toLowerCase());
        var filters = {};
        $("input.student-goals-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });

        studentGoalsViewModel.filterDesc = '';
        if (filters['most-recent']) {
            studentGoalsViewModel.filterDesc += 'יעדים שעבדו עליהם לאחרונה';
        }
        if (filters['in-progress']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'יעדים בהתקדמות';
        }
        if (filters['struggling']) {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'תלמידים מתקשים';
        }
        if (filter_text != '') {
            if (studentGoalsViewModel.filterDesc != '') studentGoalsViewModel.filterDesc += ', ';
            studentGoalsViewModel.filterDesc += 'תלמידים/יעדים תואמים "' + filter_text + '"';
        }
        if (studentGoalsViewModel.filterDesc != '')
            studentGoalsViewModel.filterDesc = 'מציג רק ' + studentGoalsViewModel.filterDesc;
        else
            studentGoalsViewModel.filterDesc = 'אין סינון';

        var container = $('#class-student-goal').detach();

        $.each(studentGoalsViewModel.rowData, function(idx, row) {
            var row_visible = true;

            if (filters['most-recent']) {
                row_visible = row_visible && (!row.goal || (row.goal == row.student.most_recent_update));
            }
            if (filters['in-progress']) {
                row_visible = row_visible && (row.goal && (row.progress_count > 0));
            }
            if (filters['struggling']) {
                row_visible = row_visible && (row.struggling);
            }
            if (row_visible) {
                if (filter_text == '' || row.student.nickname.toLowerCase().indexOf(filter_text) >= 0) {
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            $(objective.blockElement).removeClass('matches-filter');
                        });
                    }
                } else {
                    row_visible = false;
                    if (row.goal) {
                        $.each(row.goal.objectives, function(idx, objective) {
                            if ((objective.description.toLowerCase().indexOf(filter_text) >= 0)) {
                                row_visible = true;
                                $(objective.blockElement).addClass('matches-filter');
                            } else {
                                $(objective.blockElement).removeClass('matches-filter');
                            }
                        });
                    }
                }
            }

            if (row_visible)
                $(row.rowElement).show();
            else
                $(row.rowElement).hide();

            if (filters['most-recent'])
                row.countElement.hide();
            else
                row.countElement.show();
        });

        container.insertAfter('#class-goal-filter-desc');

        ClassProfile.updateStudentGoalsFilterText(studentGoalsViewModel);
    },
    finishLoadGraph: function(data, href, fNoHistoryEntry, apiCallback) {

        this.fLoadingGraph = false;

        if (!fNoHistoryEntry) {
            // Add history entry for browser
            //             if ($.address) {
            //                 $.address(href);
            // }
        }

        this.showGraphThrobber(false);
        this.styleSublinkFromHref(href);

        var start = (new Date).getTime();
        if (apiCallback) {
            apiCallback(data, href);
        } else {
            $("#graph-content").html(data);
        }
        var diff = (new Date).getTime() - start;
        KAConsole.log('API call rendered in ' + diff + ' ms.');
    },

    finishLoadGraphError: function() {
        this.fLoadingGraph = false;
        this.showGraphThrobber(false);
        $("#graph-content").html("<div class='graph-notification'>"+
            "אופס... נתקלנו בתקלה כשניסינו לטעון את הגרף. " +
            "אנא נסו שוב מאוחר יותר, ואם התקלה חוזרה אנא " +
            "<a href='/reportissue?type=Defect'>דווחו לנו</a>.</div>");
    },

    // TODO: move history management out to a common utility
    historyChange: function(e) {
        var href = ( $.address.value() === "/" ) ? this.initialGraphUrl : $.address.value();
        var url = ( $.address.path() === "/" ) ? this.initialGraphUrl : $.address.path();

        if ( href ) {
            if ( this.expandAccordionForHref(href) ) {
                this.loadGraph( href , true );
                this.loadFilters( url );
            } else {
                // Invalid URL - just try the first link available.
                var links = $(".graph-link");
                if ( links.length ) {
                    ClassProfile.loadGraphFromLink( links[0] );
                }
            }
        }
    },

    showGraphThrobber: function(fVisible) {
        if (fVisible) {
            $("#graph-progress-bar").progressbar({value: 100}).slideDown("fast");
        } else {
            $("#graph-progress-bar").slideUp("fast", function() {
                $(this).hide();
            });
        }
    },

    // TODO: move this out to a more generic utility file.
    parseQueryString: function(url) {
        var qs = {};
        var parts = url.split('?');
        if(parts.length == 2) {
            var querystring = parts[1].split('&');
            for(var i = 0; i<querystring.length; i++) {
                var kv = querystring[i].split('=');
                if(kv[0].length > 0) { //fix trailing &
                    key = decodeURIComponent(kv[0]);
                    value = decodeURIComponent(kv[1]);
                    qs[key] = value;
                }
            }
        }
        return qs;
    },

    // TODO: move this out to a more generic utility file.
    reconstructQueryString: function(hash, kvjoin, eljoin) {
        kvjoin = kvjoin || '=';
        eljoin = eljoin || '&';
        qs = [];
        for(var key in hash) {
            if(hash.hasOwnProperty(key))
                qs.push(key + kvjoin + hash[key]);
        }
        return qs.join(eljoin);
    },

    // TODO: this is redundant with addobjectivehover in profile.js
    AddObjectiveHover: function(element) {
        var infoHover = $("#info-hover-container");
        if (infoHover.length === 0) {
            infoHover = $('<div id="info-hover-container"></div>').appendTo("body");
        }
        var lastHoverTime;
        var mouseX;
        var mouseY;
        element.find(".objective").hover(
            function(e) {
                var hoverTime = +(new Date);
                lastHoverTime = hoverTime;
                mouseX = e.pageX;
                mouseY = e.pageY;
                var self = this;
                setTimeout(function() {
                    if (hoverTime != lastHoverTime) {
                        return;
                    }

                    var hoverData = $(self).children(".hover-data");
                    if ($.trim(hoverData.html())) {
                        infoHover.html($.trim(hoverData.html()));

                        var left = mouseX + 15;
                        var jelGraph = $("#graph-content");
                        var leftMax = jelGraph.offset().left +
                                jelGraph.width() - 150;

                        infoHover.css('left', Math.min(left, leftMax));
                        infoHover.css('top', mouseY + 5);
                        infoHover.css('cursor', 'pointer');
                        infoHover.css('position', 'fixed');
                        infoHover.show();
                    }
                }, 100);
            },
            function(e){
                lastHoverTime = null;
                $("#info-hover-container").hide();
            }
        );
    },

    getStudentListFromId: function (list_id) {
        var student_list;
        jQuery.each(this.studentLists, function(i,l) {
            if (l.key == list_id) {
                student_list = l;
                return false;
            }
        });
        return student_list;
    },

    // called whenever user selects student list dropdown
    updateStudentList: function(event, ui) {
        // change which item has the selected attribute
        // weird stuff happening with .data(), just use attr for now...
        var $dropdown = $('#studentlists_dropdown ol');
        $dropdown.children('li[data-selected=selected]').removeAttr('data-selected');
        $(ui.item).attr('data-selected', 'selected');

        // store which class list is selected
        var student_list = ClassProfile.getStudentListFromId(ui.item.data('list_id'));
        $dropdown.data('selected', student_list);

        // update the address parameter
        $.address.parameter("list_id",ui.item.data('list_id'))

        // update appearance of dropdown
        $('#studentlists_dropdown .ui-button-text').text(student_list.name);
        $dropdown.hide();

        $('#count_students').html('&hellip;');
        $('#energy-points .energy-points-badge').html('&hellip;');
    },

    updateStudentInfo: function(students, energyPoints) {
        $('#count_students').text(students + '');
        if ( typeof energyPoints !== "string" ) {
            energyPoints = addCommas(energyPoints);
        }
        $('#energy-points .energy-points-badge').text(energyPoints);
    },

    renderStudentProgressReport: function(data, href) {
        ClassProfile.updateStudentInfo(data.progress_data.length, data.c_points);

        $.each(data.exercise_names, function(idx, exercise) {
            exercise.type = "exercise";
            exercise.isExercise = true;
        });

        $.each(data.video_names, function(idx, video) {
            video.type = "video";
            video.isExercise = false;
        });

        data.progress_names = data.exercise_names.concat(data.video_names);
        $.each(data.progress_names, function(idx, item) {
            item.display_name_lower = item.display_name.toLowerCase();
            item.idx = idx;
        });

        data.students = [];
        $.each(data.progress_data, function(idx, student_row) {
            data.students.push(student_row);
        });
        data.students.sort(function(a, b) { if (a.nickname < b.nickname) return -1; else if (b.nickname < a.nickname) return 1; return 0; });

        $.each(data.students, function(idx, student_row) {
            student_row.idx = idx;
            student_row.nickname_lower = student_row.nickname.toLowerCase();
            var lastIdx = 0;
            $.each(student_row.exercises, function(idx2, exercise) {
                exercise.type = "exercise";
                exercise.idx = idx2;
                exercise.display_name = data.exercise_names[idx2].display_name;
                exercise.progress = (exercise.progress*100).toFixed(0);
                // TODO: awkward turtle, replace w normal href
                exercise.link = student_row.profile_root
                                    + "/vital-statistics/exercise-problems/"
                                    + data.exercise_names[idx2].name;
                if (exercise.last_done) {
                    exercise.seconds_since_done = ((new Date()).getTime() - Date.parse(exercise.last_done)) / 1000;
                } else {
                    exercise.seconds_since_done = -1;
                }

                exercise.notTransparent = true;
                if (exercise.status_name == 'review')
                    exercise.status_css = 'review light';
                else if (exercise.status_name == 'not-started') {
                    exercise.status_css = 'transparent';
                    exercise.notTransparent = false;
                } else
                    exercise.status_css = exercise.status_name;

                lastIdx = idx2 + 1;
            });

            $.each(student_row.videos, function(idx2, video) {
                video.type = "video";
                video.idx = lastIdx + idx2;
                video.display_name = data.progress_names[lastIdx + idx2].display_name;

                video.notTransparent = true;
                if (video.status_name == 'not-started') {
                    video.status_css = 'transparent';
                    video.notTransparent = false;
                } else
                    video.status_css = video.status_name;
                video.link = "/video/" + data.video_names[idx2].name;
            });

            student_row.progress = student_row.exercises.concat(student_row.videos);
        });

        Handlebars.registerHelper("toTopicName", function(idx) {
            return data.topic_names[idx];
        });
        Handlebars.registerHelper("toStatusText", function(type, status) {
            return ClassProfile.statusInfo[type][status];
        });

        var template = Templates.get( "profile.profile-class-progress-report" );

        $("#graph-content").html( template(data) );
        ProgressReport.init(data);
    }
};

var ProgressReport = {

    updateFilterTimeout: null,

    studentRowView: Backbone.View.extend({
        initialize: function() {
            this.columnViews = [];
        },

        updateFilter: function(visibleColumns) {
            if (this.model.visible) {
                if (this.model.highlight && this.options.allowHighlight) {
                    $(this.el).addClass('highlight');
                } else {
                    $(this.el).removeClass('highlight');
                }

                if (this.model.hiddenCount) {
                    $(this.el).find('.hidden-students').html('(' + this.model.hiddenCount + ' חבויים)');
                }

                $(this.el).show();

                $.each(this.columnViews, function(idx, columnView) {
                    columnView.updateFilter(visibleColumns, null, this.model.matchingCells);
                });
            } else {
                $(this.el).hide();
            }
        }
    }),
    studentColumnView: Backbone.View.extend({
        updateFilter: function(visibleColumns, matchingColumns, matchingCells) {
            if (visibleColumns[this.options.index]) {
                if (matchingColumns && matchingColumns[this.options.index]) {
                    $(this.el).addClass('highlight');
                    if (matchingColumns[this.options.index] == "name") {
                        $(this.el).find(".item-name").addClass("filter-match");
                    }
                } else {
                    $(this.el).removeClass('highlight');
                }

                if (matchingCells && !matchingCells[this.options.index]) {
                    $(this.el).addClass('notmatching');
                } else {
                    $(this.el).removeClass('notmatching');
                }

                $(this.el).show();
            } else {
                $(this.el).hide();
            }
        }
    }),

    init: function(model) {
        var self = this;

        this.model = model;
        this.rowViews = [];
        this.headingViews = [];
        this.hiddenStudentsModel = {
            'visible': false,
            'highlight': false,
            'hiddenCount': 10
        };

        if ($.browser.msie && parseInt($.browser.version) < 8) {
            this.showBrowserRequirements();
            return;
        }

        var adjustData = this.preAdjustTable();
        temporaryDetachElement($('#module-progress'), function() {
            this.adjustTable(adjustData);
        }, this);

        this.onResize();
        $("#module-progress td.student-module-status").hover(this.onHover, this.onUnhover);

        if (!window.fBoundProgressReport) {
            $(window).resize(ProgressReport.onResize);
            $(document).mousemove(function(e){window.mouseX = e.pageX; window.mouseY = e.pageY;});
            window.fBoundProgressReport = true;
        }

        $('#module-progress').find('th.student-exercises-col').each(function() {
            var col_idx = $(this).attr('data-id');
            self.headingViews.push(new ProgressReport.studentColumnView({
                el: this,
                model: null,
                index: col_idx
            }));
        });
        $('#module-progress').find('tr.student-email-row').each(function() {
            var row_idx = $(this).attr('data-id');
            var row = (row_idx >= 0) ? model.students[row_idx] : self.hiddenStudentsModel;
            self.rowViews.push(new ProgressReport.studentRowView({
                el: this,
                model: row,
                allowHighlight: true
            }));
        });
        $('#module-progress').find('tr.student-exercises-row').each(function() {
            var row_idx = $(this).attr('data-id');
            var row = (row_idx >= 0) ? model.students[row_idx] : self.hiddenStudentsModel;
            var rowView = new ProgressReport.studentRowView({
                el: this,
                model: row
            });
            self.rowViews.push(rowView);

            $(this).find('td.student-module-status').each(function() {
                var col_idx = $(this).attr('data-id');
                rowView.columnViews.push(new ProgressReport.studentColumnView({
                    el: this,
                    model: row,
                    index: col_idx
                }));
                $(this).click(function() {
                    // TODO: awkward turtle this should really just be a link,
                    // but I don't feel like combing through right now.
                    window.location = row.progress[col_idx].link;
                });
            });
        });

        $("#student-progressreport-search").unbind();
        $("#student-progressreport-search").keyup(function() {
            if (ProgressReport.updateFilterTimeout == null) {
                ProgressReport.updateFilterTimeout = setTimeout(function() {
                    ProgressReport.filterRows(model);
                    ProgressReport.updateFilterTimeout = null;
                }, 250);
            }
        });

        $("input.progressreport-filter-check").unbind();
        $("input.progressreport-filter-check").change(function() { ProgressReport.filterRows(model); });
        $("#progressreport-filter-last-time").change(function() {
            $("input.progressreport-filter-check[name=\"recent\"]").attr("checked", true);
            ProgressReport.filterRows(model);
        });

        $(".progress-type-radio").change(function() {
            ProgressReport.filterRows(model);
        });

        $("#module-progress .tableHeader .topic-name a").click(function(e) {
            e.preventDefault();
            if ($("#student-progressreport-search").val() == e.srcElement.text) {
                $("#student-progressreport-search").val("");
            } else {
                $("#student-progressreport-search").val(e.srcElement.text);
            }
            ProgressReport.filterRows(model);
        });

        ProgressReport.filterRows(model);
    },

    filterRows: function(model) {

        var progressType = $(".progress-type-radio:checked").val();

        // Videos can't be filtered by time
        var time_filter_disabled = (progressType == "video");
        $("#progressreport-filter-last-time").prop("disabled", time_filter_disabled);
        $("#progressreport-recent").prop("disabled", time_filter_disabled);
        $("#progressreport-struggling").prop("disabled", time_filter_disabled);
        if (time_filter_disabled == true) {
            $("#progressreport-recent").prop("checked", false);
            $("#progressreport-struggling").prop("checked", false);
        }
        $(".graph-options").children().hide();
        $("#"+progressType+"-progress-legend").show();

        var filterText = $.trim($('#student-progressreport-search').val().toLowerCase());
        var filters = {};
        $("input.progressreport-filter-check").each(function(idx, element) {
            filters[$(element).attr('name')] = $(element).is(":checked");
        });
        var filterRecentTime = $("#progressreport-filter-last-time").val();

        var visibleColumns = [];
        var matchingColumns = [];
        var hiddenCount = 0;

        // Match topic names
        var matchingTopics = [];
        $(".filter-match").removeClass("filter-match")
        if (filterText.length > 1) {
            $.each(model.topic_names, function(idx, name) {
                if (name.indexOf(filterText) > -1) {
                    matchingTopics.push(parseInt(idx));
                    $(".topic-name[data-id=" + idx + "]").addClass("filter-match");
                }
            });
        }

        // Match columns with filter text
        $.each(model.progress_names, function(idx, exercise) {
            matchingColumns[idx] = false;
            visibleColumns[idx] = true;
            if (filterText.length > 1) {
                if (exercise.display_name_lower.indexOf(filterText) > -1) {
                    matchingColumns[idx] = "name";
                } else if (_.intersection(exercise.topics, matchingTopics).length > 0) {
                    matchingColumns[idx] = "topic";
                } else {
                    visibleColumns[idx] = false;
                }
            }
        });

        // Match rows with filter text
        $.each(model.students, function(idx, studentRow) {
            var foundMatchingExercise = false;
            var matchesFilter = filterText.length <= 1 || studentRow.nickname_lower.indexOf(filterText) > -1;
            $.each(studentRow.progress, function(idx2, exercise) {
                if (exercise.status_name != '' && matchingColumns[idx2]) {
                    foundMatchingExercise = true;
                    return false;
                }
            });

            if (foundMatchingExercise || matchesFilter) {

                studentRow.visible = true;
                studentRow.highlight = matchesFilter && (filterText.length > 1);

                if (matchesFilter) {
                    $.each(studentRow.progress, function(idx2, exercise) {
                        if (exercise.status_name != '')
                            visibleColumns[idx2] = true;
                    });
                }
            } else {
                studentRow.visible = false;
                hiddenCount++;
            }
        });

        // "Struggling" filter
        if (filters['struggling'] || filters['recent']) {
            var filteredColumns = [];

            // Hide students who are not struggling in one of the visible columns
            $.each(model.students, function(idx, studentRow) {
                if (studentRow.visible) {
                    var foundValid = false;
                    studentRow.matchingCells = [];
                    $.each(studentRow.progress, function(idx2, exercise) {
                        var valid = visibleColumns[idx2];
                        if (filters['struggling'] && exercise.status_css != 'struggling') {
                            valid = false;
                        } else if (filters['recent'] &&
                                    (exercise.seconds_since_done <= -1 ||
                                    exercise.seconds_since_done > 60*60*24*filterRecentTime)) {
                            valid = false;
                        }
                        if (valid) {
                            studentRow.matchingCells[idx2] = true;
                            filteredColumns[idx2] = true;
                            foundValid = true;
                        } else {
                            studentRow.matchingCells[idx2] = (exercise.status_name == '');
                        }
                    });
                    if (!foundValid) {
                        studentRow.visible = false;
                        hiddenCount++;
                    }
                }
            });

            // Hide columns that don't match the filter
            $.each(model.progress_names, function(idx, exercise) {
                if (!matchingColumns[idx] && !filteredColumns[idx])
                    visibleColumns[idx] = false;
            });
        } else {
            $.each(model.students, function(idx, studentRow) {
                studentRow.matchingCells = null;
            });
        }


        $.each(model.progress_names, function(idx, progress) {
            if (progress.type != progressType) {
                matchingColumns[idx] = false;
                visibleColumns[idx] = false;
            }
        });

        this.hiddenStudentsModel.visible = (hiddenCount > 0);
        this.hiddenStudentsModel.hiddenCount = hiddenCount;

        temporaryDetachElement($('#module-progress'), function() {
            _.each(this.rowViews, function(rowView) {
                rowView.updateFilter(visibleColumns);
            });
            _.each(this.headingViews, function(colView) {
                // per column list of visible rows, list of highlighted rows
                colView.updateFilter(visibleColumns, matchingColumns);
            });
        }, this);

        var adjustData = this.preAdjustTable();
        temporaryDetachElement($('#module-progress'), function() {
            this.adjustTable(adjustData);
        }, this);
    },

    showBrowserRequirements: function() {
        $("#module-progress").replaceWith("<div class='graph-notification'>This chart requires a newer browser such as Google Chrome, Safari, Firefox, or Internet Explorer 8+.</div>");
    },

    hoverDiv: function() {
        if (!window.elProgressReportHoverDiv)
        {
            window.elProgressReportHoverDiv = $("<div class='exercise-info-hover' style='position:absolute;display:none;'></div>");
            $(document.body).append(window.elProgressReportHoverDiv);
        }
        return window.elProgressReportHoverDiv;
    },

    onHover: function() {
        var dtLastHover = window.dtLastHover = new Date();
        var self = this;
        setTimeout(function(){
            if (dtLastHover != window.dtLastHover) return;

            var sHover = $(self).find(".hover-content");
            if (sHover.length)
            {
                var jelHover = $(ProgressReport.hoverDiv());
                jelHover.html(sHover.html());

                var left = window.mouseX + 15;
                if (left + 150 > $(window).scrollLeft() + $(window).width()) left -= 150;

                var top = window.mouseY + 5;
                if (top + 115 > $(window).scrollTop() + $(window).height()) top -= 115;

                jelHover.css('left', left).css('top', top);
                jelHover.css('cursor', 'pointer');
                jelHover.show();
            }
        }, 100);
    },

    onUnhover: function() {
        window.dtLastHover = null;
        $(ProgressReport.hoverDiv()).hide();
    },

    onScroll: function() {

        var jelTable = $("#table_div");
        var jelHeader = $("#divHeader");
        var jelColumn = $("#firstcol");

        var leftTable = jelTable.scrollLeft();
        var topTable = jelTable.scrollTop();

        var leftHeader = jelHeader.scrollLeft(leftTable).scrollLeft();
        var topColumn = jelColumn.scrollTop(topTable).scrollTop();

        if (leftHeader < leftTable)
        {
            jelHeader.children().first().css("padding-right", 20);
            jelHeader.scrollLeft(leftTable);
        }

        if (topColumn < topTable)
        {
            jelColumn.children().first().css("padding-bottom", 20);
            jelColumn.scrollTop(topTable);
        }
    },

    onResize: function() {

        var width = $("#graph-content").width() - $("#firstTd").width() - 12;
        $(".sizeOnResize").width(width);

    },

    preAdjustTable: function() {

        var adjustData = { tableHeaderWidths: [] };

        // From http://fixed-header-using-jquery.blogspot.com/2009/05/scrollable-table-with-fixed-header-and.html
        //
        var columns = $('#divHeader th:visible');
        var colCount = columns.length-1; //get total number of column

        var m = 0;
        adjustData.brow = 'mozilla';

        jQuery.each(jQuery.browser, function(i, val) {
            if(val == true){
                adjustData.brow = i.toString();
            }
        });

        adjustData.tableDiv = $("#module-progress #table_div");
        adjustData.firstTd = $('#firstTd');
        adjustData.newFirstTdWidth = $('.tableFirstCol:visible').width();
        adjustData.tableHeaderHeight = adjustData.firstTd.height();

        $('#table_div td:visible:lt(' + colCount +')').each(function(index, element) {
            var colIdx = $(this).attr('data-id');
            var cellWidth = $(this).width();
            if (adjustData.brow == 'msie'){
                cellWidth -= 2; //In IE there is difference of 2 px
            }
            adjustData.tableHeaderWidths[colIdx] = { 'width': cellWidth };
        });

        columns.each(function(index, element){
            var colIdx = $(element).attr('data-id');
            if (colIdx) {
                if (adjustData.tableHeaderWidths[colIdx]) {
                    adjustData.tableHeaderWidths[colIdx].header = $(this).find('div.tableHeader');
                    adjustData.tableHeaderWidths[colIdx].headerTh = $(this);
                }
            }
        });

        return adjustData;
    },

    adjustTable: function(adjustData) {

        if (adjustData.brow == 'chrome' || adjustData.brow == 'safari') {
            adjustData.tableDiv.css('top', '1px');
        }

        adjustData.firstTd.css("width",adjustData.newFirstTdWidth);//for adjusting first td
        $.each(adjustData.tableHeaderWidths, function(idx, headerWidth) {
            if (headerWidth)
                if (headerWidth.width >= 0) {
                    $(headerWidth.header).width(headerWidth.width);
                    $(headerWidth.headerTh).height(adjustData.tableHeaderHeight);
                } else {
                    $(headerWidth.header).attr('style','');
                }
        });
    }
};
