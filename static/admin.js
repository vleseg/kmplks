function renderErrorMsg(errorMsgCntr, status, error) {
    var data = {status: status, error: error}
    errorMsgCntr.html(fromBars('error', data))
}

function fromBars(templateId, data) {
    /* Compile Handlebars template and render html with data given. */
    var template = Handlebars.compile($('#hbt-' + templateId).html());

    return template(data)
}

function deleteEntity(id, onSuccess, errorMsgCntr) {
    /* Wrapper around entity deletion API request. */
    $.ajax({
        type: 'DELETE', url: '/admin/api/entities/' + id
    })
        .done(onSuccess)
        .fail(function (xhr, status, error) {
            renderErrorMsg(errorMsgCntr, status, error)
        })
}

function fetchList(kindName, onSuccessFn, errorMsgCntr) {
    /* Wrapper around list of entities fetching API request. */
    $.getJSON('/admin/api/' + kindName + '/entities', onSuccessFn)
        .fail(function (xhr, status, error) {
            renderErrorMsg(errorMsgCntr, status, error)
        })
}

$(document).ready(function () {
    // Get and build main list of entities for the kind.
    // Main list allows to delete underlying entities or open them for editing.
    var mainListTabLabelsCtnr = $('#ka-mainlist-tab-labels');
    if (mainListTabLabelsCtnr.length > 0) {
        // Datastore initialization button click trigger.
        mainListTabLabelsCtnr.find('#ka-mainlist-init-button')
            .on('click', function () {
                $.ajax('/admin/api/initialize')
            });
        // Triggers for tabs.
        mainListTabLabelsCtnr.find('a').on('shown.bs.tab', function (e) {
            var kind = $(e.target).data('kind');  // i. e. kind name
            var verboseKind;  // i. e. kind name in Russian

            // Tab, that was opened
            var tab = $('#ka-mainlist-tabs').find('#ka-mainlist-tab-' + kind);

            var itemsCtnr = tab.find('.tab-pane-items');
            // Tab is cleared of any previous content, incl. errors.
            // TODO: clear tab only if it contains only an error message
            itemsCtnr.empty();

            fetchList(kind, function (data) {
                // On success compile template, render list and change page
                // header.
                itemsCtnr.html(fromBars('mainlist', data));
                verboseKind = data['kind'];
                $('#ka-mainlist-header').text(data['kind_plural'])
            }, itemsCtnr);

            itemsCtnr.on('click', function (e) {
//                e.preventDefault();
                var target = $(e.target);
                var entry = target.closest('.ka-mainlist-item');

                // If 'delete' icon/button is clicked, show 'delete entity
                // confirmation' modal.
                if (target.hasClass("ka-mainlist-delete")) {
                    var modalData = {
                        'kind': kind, 'id': entry.data('id'),
                        'verboseKind': verboseKind, 'repr': entry.data('repr')
                    };
                    $('#ka-delete-entity-modal').data(modalData).modal()
                }
                // If 'add new item' link is clicked open edit form for new
                // entity
                else if (target.hasClass('ka-mainlist-new')) {
                    window.open('/admin/new?kind=' + kind, '_blank')
                }
                // If list item was clicked go to edit form for corresponding
                // entity
                else if (target.hasClass('ka-mainlist-item')) {
                    var id = entry.data('id');
                    window.open('/admin/edit?id=' + id, '_blank');
                    e.stopPropagation();
                }
            })
        });

        $('a[data-kind=Service]').click()
    }

    // Delete entity modal logic.
    var modal = $('#ka-delete-entity-modal');
    if (modal.length > 0) {
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
                variableContent.append(fromBars('success', {
                    'message': 'Объект успешно удален.'
                }));
                modal.data({'mustRefresh': true})
            }, variableContent);
        });
        modal.on('hidden.bs.modal', function (e) {
            variableContent.empty().hide();
            defaultContent.show();
            if (modal.data('mustRefresh')) {
                // If called from main list, reload current tab to make changes
                // visible.
                var tabLabel = $('#ka-mainlist-tab-labels').find('.active');
                tabLabel.removeClass('active');
                tabLabel.find('a').tab('show');
            }
            else if (modal.data('mustClose')) {
                // If called from entity edit page, close current tab.
                window.close()
            }
        })
    }
});