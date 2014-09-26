function deleteEntity(id, onSuccess, onFail) {
    $.ajax({
        type: 'DELETE',
        url: '/admin/api/entities/' + id
    })
        .done(onSuccess)
        .fail(function (xhr, status, error) {
            onFail({'status': status, 'error': error})
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
                console.log(target, entry);
                if (target.hasClass("ka-biglist-delete-entity")) {
                    var modalData = {
                        'id': entry.data('id'),
                        'verboseKind': verboseKind,
                        'repr': entry.data('repr'),
                        'isDocument': kind == 'Document'
                    };
                    $('body')
                        .append(fromBars('hbt-delete-entity-modal', modalData));

                    var modal = $('#ka-delete-entity-modal');
                    modal.modal();
                    modal.on('hidden.bs.modal', function (e) {
                        $(e.target).remove()
                    });
                    modal.find('#ka-confirm-delete').on('click', function (e) {
                        var modalBody = modal.find('.modal-body');
                        modalBody.html(fromBars('hbt-ajax-loader'));
                        $(e.target).remove();
                        modal.find('#ka-close-modal').text('Закрыть');
                        deleteEntity(entry.data('id'), function() {
                            // On success display success message
                            modalBody.html(fromBars('hbt-success'), {
                                'msg': 'Объект успешно удален.'
                            })
                        }, function (status, error) {
                            // On error display error message
                            modalBody.html(fromBars('hbt-error', {
                                'status': status,
                                'error': error
                            }))
                        })
                    })
                }
                else if (target.closest('.ka-biglist-new')) {
                    window.open('/admin/new?kind=' + kind, '_blank')
                }
                else if (target.closest('.ka-biglist-entry')) {
                    var id = entry.data('id');
                    window
                        .open('/admin/edit?id=' + id , '_blank');
                    e.stopPropagation();
                }
            })
        });

        $('a[data-kind=Service]').click()
    }

    // Invoking entity delete modal
    $("#delete-entity-modal").on("show.bs.modal", function(e) {
        var invoker = $(e.relatedTarget);
        var modal = $(e.target);
        var resultModalBody =
            $("#delete-entity-result-modal").find(".modal-body");

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
                resultModalBody.html(fromBars('hbt-success'))
            }, function (jqXHR, textStatus, errorThrown) {
                // On error, show error message
                resultModalBody.html(fromBars('hbt-error', {
                    'status': textStatus,
                    'error': errorThrown
                }))
            });
        })
    })
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