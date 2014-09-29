function deleteEntity(id, onSuccess, onFail) {
    $.ajax({
        type: 'DELETE',
        url: '/admin/api/entities/' + id
    })
        .done(onSuccess)
        .fail(function (xhr, status, error) {
            onFail(status, error)
        })
}

function fetchAndRenderList(kindName, onSuccess, onFail) {
    $.getJSON('/admin/api/' + kindName + '/entities', onSuccess)
        .fail(function (xhr, status, error) {
            onFail({'status': status, 'error': error})
        })
}

function fromBars(templateId, data) {
    /* Compile Handlebars template and render html with data given. */
    var template = Handlebars.compile($('#' + templateId).html());
    return template(data)
}

$(document).ready(function () {
    // Attack ajax loader to page.
    var ajaxLoaderCntnr = $('.ajax-loader-container');
    if (ajaxLoaderCntnr)
        ajaxLoaderCntnr.append($(fromBars('hbt-ajax-loader')));

    // Getting and building list of entities for a kind.
    var bigListTabLabelsCntnr = $('#ka-biglist-tab-labels');
    if (bigListTabLabelsCntnr) {
        bigListTabLabelsCntnr.find('a').on('shown.bs.tab', function (e) {
            var kind = $(e.target).data('kind');
            var verboseKind;

            var bigListTabs = $('#ka-biglist-tabs');
            var tab = bigListTabs.find('#ka-biglist-tab-' + kind);

            var itemsCntnr = tab.find('.tab-pane-items');
            itemsCntnr.empty();

            fetchAndRenderList(kind, function (data) {
                // On success compile template and render list.
                itemsCntnr.html(fromBars('hbt-biglist', data));
                verboseKind = data['kind']
            }, function (status, error) {
                itemsCntnr.html(fromBars('hbt-error', {
                    'status': status,
                    'error': error
                }))
            });

            itemsCntnr.on('click', function (e) {
                e.preventDefault();
                var target = $(e.target);
                var entry = target.closest('.ka-biglist-entry');

                // If 'delete' icon/button is clicked, show 'delete entity
                // confirmation' modal.
                if (target.hasClass("ka-biglist-delete")) {
                    var modalData = {
                        'kind': kind,
                        'id': entry.data('id'),
                        'verboseKind': verboseKind,
                        'repr': entry.data('repr'),
                    };
                    $('#ka-delete-entity-modal').data(modalData).modal()
                }
                // If 'add new item' link is clicked open edit form for new
                // entity
                else if (target.closest('.ka-biglist-new')) {
                    window.open('/admin/new?kind=' + kind, '_blank')
                }
                // If list item was clicked go to edit form for corresponding
                // entity
                else if (target.closest('.ka-biglist-entry')) {
                    var id = entry.data('id');
                    window.open('/admin/edit?id=' + id, '_blank');
                    e.stopPropagation();
                }
            })
        });

        $('a[data-kind=Service]').click()
    }

    // Delete entity modal logic
    var modal = $('#ka-delete-entity-modal');
    if (modal) {
        var defaultContent = modal.find('.default-content');
        var variableContent = modal.find('.variable-content');

        modal.on('show.bs.modal', function () {
            var data = modal.data();
            $('#ka-verbose-kind').text(data.verboseKind);
            $('#ka-repr').text(data.repr);
            var cascadeDeleteWarning = $('#ka-cascade-delete-warning');
            if (data.kind == 'Document') cascadeDeleteWarning.show();
            else cascadeDeleteWarning.hide();
        });
        modal.find('#ka-confirm-delete').on('click', function () {
            defaultContent.hide();
            variableContent.show();

            modal.find('#ka-close-modal').text('Закрыть');
            deleteEntity(modal.data('id'), function() {
                // On success display success message.
                variableContent.append(fromBars('hbt-success', {
                    'message': 'Объект успешно удален.'
                }));
                modal.data({'mustRefresh': true})
            }, function (status, error) {
                // On fail display error message.
                variableContent.append(fromBars('hbt-error', {
                    'status': status,
                    'error': error
                }))
            });
        });
        modal.on('hidden.bs.modal', function (e) {
            variableContent.empty().hide();
            defaultContent.show();
            if (modal.data('mustRefresh')) {
                // Reload current tab to make changes visible.
                var tabLabel = $('#ka-biglist-tab-labels').find('.active');
                tabLabel.removeClass('active');
                tabLabel.find('a').tab('show');
            }
        })
    }
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