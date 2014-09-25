function deleteEntity(id, onSuccess, onFail) {
    $.ajax({
        type: 'DELETE',
        url: '/admin/api/entities/' + id
    })
        .done(onSuccess)
        .fail(onFail)
}

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
                listInTabs.data({
                    'kind': reqKind,
                    'verboseKind': data['kind']
                });
            }, function (jqXHR, textStatus, errorThrown) {
                // On error, show error message
                htmlFromBars('hbt-error', {
                    'status': textStatus,
                    'error': errorThrown
                })
            });
        });

        listInTabs.find('a[href=#Service]').tab('show')
    }

    // Invoking entity delete modal
    $("#delete-entity-modal").on("show.bs.modal", function(e) {
        var invoker = $(e.relatedTarget);
        var modal = $(e.target);
        var resultModalBody =
            $("#delete-entity-result-modal").find(".modal-body");

        // If called from entities list page.
        if (listInTabs) {
            var isDocument = listInTabs.data('kind') == 'Document';
            var verboseKind = listInTabs.data('verboseKind');
            var repr = invoker.prev().text();
            var prev_href = invoker.prev().attr('href');
            var id = prev_href.slice(prev_href.indexOf('?id='), 4)
        }

        var relativesWarning = modal.find('#del-relatives-warning');
        if (isDocument) relativesWarning.hide();
        else relativesWarning.show();

        modal.find('#del-entity-kind').text(verboseKind);
        modal.find('#del-entity-repr').text(repr);

        $('#confirm-delete-btn').click(function () {
            var btn = $(this);
            btn.button('loading');
            btn.button('reset');
            modal.hide();
            deleteEntity(id, function () {
                // On success, show 'successfully' deleted message.
                resultModalBody.html(htmlFromBars('hbt-success'))
            }, function (jqXHR, textStatus, errorThrown) {
                // On error, show error message
                resultModalBody.html(htmlFromBars('hbt-error', {
                    'status': textStatus,
                    'error': errorThrown
                }))
            });
        })
    })
});