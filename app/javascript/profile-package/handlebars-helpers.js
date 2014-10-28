Handlebars.registerHelper("encodeURIComponent", function(str) {
    return encodeURIComponent(str);
});

Handlebars.registerHelper("commafy", function(numPoints) {
    // From KhanUtil.commafy in math-format.js
    return numPoints.toString().replace(/(\d)(?=(\d{3})+$)/g, "$1,");
});

Handlebars.registerHelper("pluralize", function(num) {
    return (num === 1) ? "" : "s";
});

/**
 * Convert number of seconds to a time phrase for recent activity video entries.
 * Stolen from templatefilters.py
 */
Handlebars.registerHelper("secondsToTime", function(seconds) {
    // TODO: bring out KhanUtil's plural function
    // or somehow clean up the > 1 ? "s" : "" mess
    var years = Math.floor(seconds / (86400 * 365));
    seconds -= years * (86400 * 365);

    var days = Math.floor(seconds / 86400);
    seconds -= days * 86400;

    var months = Math.floor(days / 30.5);
    var weeks = Math.floor(days / 7);

    var hours = Math.floor(seconds / 3600);
    seconds -= hours * 3600;

    minutes = Math.floor(seconds / 60);
    seconds -= minutes * 60;

    if (years) {
        result = years > 1 ? (years + " שנים") : "שנה";
    } else if (months) {
        result = months > 1 ? (months + " חודשים") : "חודש";
    } else if (weeks) {
        result = weeks > 1 ? (weeks + " שבועות") : "שבוע";
    } else if (days) {
        var result = days > 1 ? (days + " יום") : "יום";
        if (hours > 1) {
            result += " ו-" + hours + " שעות";
        }
    } else if (hours) {
        var result = hours > 1 ? (hours + " שעות") : "שעה";
        if (minutes > 1) {
            result += " ו-" + minutes + " דקות";
        }
    } else if (!minutes && seconds) {
        result = seconds > 1 ? (seconds + " שניות") : "כשניה";
    } else {
        result = minutes > 1 ? (minutes + " דקות") : "כדקה";
    }
    if (!isNaN(parseInt(result[0]))) {
        result = "-" + result;
    }
    return result;
});
