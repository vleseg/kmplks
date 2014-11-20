$(document).ready(function () {
    // Attach ajax loader to page.
    var ajaxLoaderCtnr = $('.ajax-loader-container');
    if (ajaxLoaderCtnr.length > 0)
        ajaxLoaderCtnr.append($(fromBars('ajax-loader')));
});

// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $(".ajax-loader-container").show();
    },
    complete:function(){
        $(".ajax-loader-container").hide();
    }
});