var Homepage = {

    init: function() {
        VideoControls.initThumbnails();
        Homepage.initWaypoints();
        Homepage.loadData();
        Homepage.initNavigation();
    },

    initPlaceholder: function(youtube_id) {

        var jelPlaceholder = $("#main-video-placeholder");

        // Once the youtube player is all loaded and ready, clicking the play
        // button will play inline.
        $(VideoControls).one("playerready", function() {

            // Before any playing, unveil and play the real youtube player
            $(VideoControls).one("beforeplay", function() {

                // Use .right to unhide the player without causing any
                // re-rendering or "pop"-in of the player.
                $(".player-loading-wrapper").css("right", 0);

                jelPlaceholder.find(".youtube-play").css("visibility", "hidden");

            });

            jelPlaceholder.click(function(e) {

                VideoControls.play();
                e.preventDefault();

            });

        });

        // Start loading the youtube player immediately,
        // and insert it wrapped in a hidden container
        var template = Templates.get("shared.youtube-player");

        jelPlaceholder
            .parents("#main-video-link")
                .after(
                    $(template({"youtubeId": youtube_id}))
                        .wrap("<div class='player-loading-wrapper'/>")
                        .parent()
            );
    },

    initWaypoints: function() {

        // Waypoint behavior not supported in IE7-
        if ($.browser.msie && parseInt($.browser.version, 10) < 8) return;

        $.waypoints.settings.scrollThrottle = 50;

        $("#browse").waypoint(function(event, direction) {

            var jel = $(this);
            var jelFixed = $("#browse-fixed");
            var jelTop = $("#back-to-top");

            jelTop.click(function() {Homepage.waypointTop(jel, jelFixed, jelTop);});

            if (direction == "down")
                Homepage.waypointVideos(jel, jelFixed, jelTop);
            else
                Homepage.waypointTop(jel, jelFixed, jelTop);
        });
    },

    waypointTop: function(jel, jelFixed, jelTop) {
        jelFixed.css("display", "none");
        if (!$.browser.msie) jelTop.css("display", "none");
    },

    waypointVideos: function(jel, jelFixed, jelTop) {
        jelFixed.css("width", jel.width()).css("display", "block");
        if (!$.browser.msie) jelTop.css("display", "block");
        if (CSSMenus.active_menu) CSSMenus.active_menu.removeClass("css-menu-js-hover");
    },

    /**
     * Loads the contents of the topic data.
     */
    loadData: function() {
        var cacheToken = window.Homepage_cacheToken;
        // Currently, this is being A/B tested with the conventional rendering
        // method (where everything is rendered on the server). If there is
        // no cache token, then we know we're using the old method, so don't
        // fetch the data.
        if (!cacheToken) {
            return;
        }
        $.ajax({
            type: "GET",
            url: "/api/v1/topics/library/compact",
            dataType: "jsonp",

            // The cacheToken is supplied by the host page to indicate when the library
            // was updated. Since it's fully cacheable, the browser can pull from the
            // local client cache if it has the data already.
            data: {"v": cacheToken},

            // Explicitly specify the callback, since jQuery will otherwise put in
            // a randomly named callback and break caching.
            jsonpCallback: "__dataCb",
            success: function(data) {
                Homepage.renderLibraryContent(data);
            },
            error: function() {
                KAConsole.log("Error loading initial library data.");
            },
            cache: true
        });
    },

    renderLibraryContent: function(topics) {
        var template = Templates.get("homepage.videolist");
        $.each(topics, function(i, topic) {
            var items = topic["children"];
            var itemsPerCol = Math.ceil(items.length / 3);
            var colHeight = itemsPerCol * 18;
            topic["colHeight"] = colHeight;
            topic["titleEncoded"] = encodeURIComponent(topic["title"]);
            for (var j = 0, item; item = items[j]; j++) {
                var col = (j / itemsPerCol) | 0;
                item["col"] = col;
                if ((j % itemsPerCol === 0) && col > 0) {
                    item["firstInCol"] = true;
                }
            }

            var container = $("#" + topic["id"] + " ol").get(0);
            if (container) {
                container.innerHTML = template(topic);
            }
        });

        topics = null;
    },

    updateHash: function(hash) {
        if (window.location.hash.slice(1) == hash) {
            // no need;
            return;
        }
        Homepage.allowOnHashChange = false;
        window.location.hash = hash;
    },

    openTopic: function(topic_id, speed, no_jump) {
        var topic_anchor = $("#" + topic_id + ".heading:first");
        if (topic_anchor.length != 1) {
            // not found
            return;
        } else if (topic_anchor.hasClass("active")) {
            console.log("topic '" + topic_id + "' already selected");
            return;
        }

        if (typeof speed == "undefined")
            speed = 500;

        // first close all sybling content (including current)
        // content < li < ul > contents
        $("#library-content-main a.heading.active").removeClass("active", speed);
        topic_anchor.addClass("active", speed);

        var to_show = topic_anchor
            .next(".content")
            .parents(".content")
            .andSelf();

        var to_hide = $("#library-content-main .content:visible")
            .not(to_show);

        to_hide.filter(":visible").slideUp(speed);
        to_show.filter(":hidden").slideDown(speed);

        setTimeout(function() { Homepage.colorizeHeaders(speed); }, speed+5);

        $("#library-content-main span.ui-icon").removeClass("ui-icon-triangle-1-s").addClass("ui-icon-triangle-1-w");
        to_show.prev().children("span.ui-icon").addClass("ui-icon-triangle-1-s").removeClass("ui-icon-triangle-1-w");

        if (no_jump) {
            return;
        }

        var scroll_target = topic_anchor.parent().offset().top;
        if (to_hide.length > 0 && to_hide.offset().top < scroll_target) {
            scroll_target -= to_hide.height();
        }
        scroll_target -= topic_anchor.outerHeight();  // give some context

        $('html, body').animate({scrollTop: scroll_target}, speed);

        Homepage.updateHash(topic_id.slice(1));
    },

    allowOnHashChange: true,

    colorizeHeaders: function(speed) {
        $("#library-content-main .heading:visible:even").addClass("even", speed);
        $("#library-content-main .heading:visible:odd").removeClass("even", speed);
    },

    initNavigation: function() {

        Homepage.colorizeHeaders();

        $("#library-content-main a.heading").click(function(event) {
            var content = $(this).next(".content");
            if (content.is(":visible")) {
                // this item is already open - close by selecting the parent
                var parent_topic = content.parents(".content:first").prev("a.heading");
                if (parent_topic.length > 0)
                    Homepage.openTopic(parent_topic[0].id);
                else
                    Homepage.openTopic(this.id);
            } else {
                Homepage.openTopic(this.id);
            }
            event.preventDefault();
        })

        $(window).on('hashchange', function(event) {
            if (!Homepage.allowOnHashChange) {
                Homepage.allowOnHashChange = true;
                event.preventDefault();
            } else {
                var topic_anchor = $("#_" + window.location.hash.slice(1) + ".heading");
                if (topic_anchor.length > 0) {
                    event.preventDefault();
                    Homepage.openTopic(topic_anchor[0].id, 0);
                }
            }
        });

        // jump to initial topic, if exists
        if (!window.location.hash.length ) {
            var first_topic = $("#library-content-main a.heading:first")[0];
            Homepage.openTopic(first_topic.id, 0, true);
        } else {
            var topic_anchor = $("#_" + window.location.hash.slice(1) + ".heading");
            if (topic_anchor.length > 0) {
                $(function() { Homepage.openTopic(topic_anchor[0].id, 0) });
            }
        }
    }
}

$(function() {Homepage.init();});

