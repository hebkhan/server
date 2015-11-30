// We don't want to load the mobile logo unless it's used
jQuery(document).ready( function() {
	var mobileLogo = jQuery("#mobile-logo");
	if (mobileLogo.length) {
		mobileLogo.attr("src", mobileLogo.data("src"));
	}
});
jQuery(document).bind("mobileinit", function() {
    $.mobile.defaultPageTransition = 'none';
	$.mobile.page.prototype.options.addBackBtn = true;
	$.mobile.page.prototype.options.backBtnText = "חזור";
});

var Notifications = {
    show: function(sNotificationContainerHtml) {},
    showTemplate: function(templateName) {},
    hide: function() {}
};
