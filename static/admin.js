function fetchAndRenderList(kindName, onSuccess, onFail) {
    $.getJSON('/admin/api/' + kindName + '/entities', onSuccess)
        .fail(function (xhr, status, error) {
            onFail({'status': status, 'error': error})
        })
}

function htmlFromBars(templateId, data) {
    /* Compile Handlebars template and render html with data given. */
    var template = Handlebars.compile($('#' + templateId).html());
    return template(data)
}

// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $(".ajax-loader-container").show();
    },
    complete:function(){
        $(".ajax-loader-container").hide();
    }
});

$(document).ready(function () {
    // Attack ajax loader to page.
    var ajax_loader_c = $('.ajax-loader-container');
    if (ajax_loader_c)
        ajax_loader_c.append($(htmlFromBars('hbt-ajax-loader')));

    // Getting and building list of entities for a kind.
    var listInTabs = $('#entities-in-tabs');
    if (listInTabs) {
        $("a[data-toggle='tab']").on("shown.bs.tab", function(e) {
            // Verbose kind name must be duplicated in content header.
            var reqKind = $(this).attr('href').slice(1);
            var reqKindVerbose = $(this).text().toUpperCase();
            $('#content-header').text(reqKindVerbose);

            var tabPaneItems = $('#' + reqKind).find('.tab-pane-items');

            // Purge previously loaded content.
            tabPaneItems.empty();

            fetchAndRenderList(reqKind, function (data) {
                // On success render list.
                tabPaneItems.html(htmlFromBars('hbt-list-in-tabs', data));
            }, function (data) {
                // On fail render error message.
                tabPaneItems.html(htmlFromBars('hbt-list-fetch-error'), data)
            });
        });

        listInTabs.find('a[href=#Service]').tab('show')
    }
});