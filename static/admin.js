function FieldsRenderingRules() {
    this.slots = {
        'int': 1, 'ref': 1, 'multi_ref': 1, 'repr': 1, 'bool': 1, 'enum': 1,
        'plain': 2, 'rich': 2
    };
}

var FRR = new FieldsRenderingRules();

function deleteEntity(id, onSuccess, onFail) {
    $.ajax({
        type: 'DELETE', url: '/admin/api/entities/' + id
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

function fetchAndRenderFields(action, toFetch, onSuccess, onFail) {
    var uriFragment;

    if (action == 'edit')
        uriFragment = 'entities/' + toFetch;
    else if (action == 'new')
        uriFragment = toFetch + '/fields';
    else
        throw new Error("Invalid action type: " + action);

    $.getJSON('/admin/api/' + uriFragment, onSuccess)
        .fail(function (xhr, status, error) {
            onFail({'status': status, 'error': error})
        })
}

function fromBars(templateId, data) {
    /* Compile Handlebars template and render html with data given. */
    var template = Handlebars.compile($('#hbt-' + templateId).html());

    return template(data)
}

function renderField(field, slotsRequired, choices) {
    var templateName = field.type.replace(/_/g, '-');
    var fieldId = 'ka-' + field.name + '-field';
    var labelHTML = fromBars('label', {
        'fieldId': fieldId,
        'labelText': field.label
    });

    var fieldHTML = fromBars(templateName, field);

    var compiled = $(fromBars('field-container', {
        'labelHTML': labelHTML, 'fieldHTML': fieldHTML,
        'isNarrow': slotsRequired == 1, 'fieldId': fieldId
    }));

    if (field.type == 'enum' || field.type == 'bool')
        compiled.find('select').val(field.value.toString());

    return compiled
}

$(document).ready(function () {
    // Attack ajax loader to page.
    var ajaxLoaderCntnr = $('.ajax-loader-container');
    if (ajaxLoaderCntnr.length > 0)
        ajaxLoaderCntnr.append($(fromBars('ajax-loader')));

    // Get and build big list of entities for the kind.
    var bigListTabLabelsCntnr = $('#ka-biglist-tab-labels');
    if (bigListTabLabelsCntnr.length > 0) {
        bigListTabLabelsCntnr.find('a').on('shown.bs.tab', function (e) {
            var kind = $(e.target).data('kind');
            var verboseKind;

            var bigListTabs = $('#ka-biglist-tabs');
            var tab = bigListTabs.find('#ka-biglist-tab-' + kind);

            var itemsCntnr = tab.find('.tab-pane-items');
            itemsCntnr.empty();

            fetchAndRenderList(kind, function (data) {
                // On success compile template and render list.
                itemsCntnr.html(fromBars('biglist', data));
                verboseKind = data['kind']
            }, function (errorData) {
                itemsCntnr.html(fromBars('error', errorData))
            });

            itemsCntnr.on('click', function (e) {
//                e.preventDefault();
                var target = $(e.target);
                var entry = target.closest('.ka-biglist-item');

                // If 'delete' icon/button is clicked, show 'delete entity
                // confirmation' modal.
                if (target.hasClass("ka-biglist-delete")) {
                    var modalData = {
                        'kind': kind, 'id': entry.data('id'),
                        'verboseKind': verboseKind, 'repr': entry.data('repr')
                    };
                    $('#ka-delete-entity-modal').data(modalData).modal()
                }
                // If 'add new item' link is clicked open edit form for new
                // entity
                else if (target.hasClass('ka-biglist-new')) {
                    window.open('/admin/new?kind=' + kind, '_blank')
                }
                // If list item was clicked go to edit form for corresponding
                // entity
                else if (target.hasClass('ka-biglist-item')) {
                    var id = entry.data('id');
                    window.open('/admin/edit?id=' + id, '_blank');
                    e.stopPropagation();
                }
            })
        });

        $('a[data-kind=Service]').click()
    }

    // Entity edit page logic.
    var entityEditForm = $('#ka-edit-form');
    if (entityEditForm.length > 0) {
        var action = entityEditForm.data('action');
        var toFetch = entityEditForm.data('toFetch');

        fetchAndRenderFields(action, toFetch, function (data) {
            // On success fetch and render fields and their content (if any).
            console.log(data);

            var freeSlots = 0;
            var currentRow;

            $.each(data.fields, function (i, field) {
                var slotsRequired = FRR.slots[field.type];
                if (freeSlots < slotsRequired) {
                    currentRow = $(fromBars('row'));
                    entityEditForm.find('fieldset').append(currentRow);
                    freeSlots = 2;
                }
                currentRow
                    .append(renderField(field, slotsRequired, data.choices));

                freeSlots = freeSlots - slotsRequired;
            });

            $('#ka-entity-repr').text(data.label);

            // Load/unload CKEditor on 'HTML'/'Plain' button toggle.
            var toggleHtmlButtons = $('button.ka-toggle-ckeditor');
            if (toggleHtmlButtons.length > 0) {
                toggleHtmlButtons.on('click', function (e) {
                    var btn = $(e.target);
                    var textareaId = btn.next().attr('id');

                    if (btn.hasClass('active')) {
                        var editorInstance = CKEDITOR.instances[textareaId];
                        editorInstance.destroy();
                        btn.text(btn.data('initialText'))
                    }
                    else {
                        btn.data({'initialText': btn.text()});
                        btn.text(btn.data('toggleText'));
                        CKEDITOR.replace(textareaId);
                    }
                })
            }

            // Activate fields on click.
            entityEditForm.on('submit', function () {

            })
        }, function (errorData) {
            // Render error message on fail.
            entityEditForm.find('fieldset').append(fromBars('error', errorData))
        });
        
        // Save changes to entity on submit.
        entityEditForm.submit(function () {
            
        });
        
        // Close window on 'Cancel' button click.
        $('#ka-edit-close-btn').click(function () {
            window.close()
        })
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
            }, function (errorData) {
                // On fail display error message.
                variableContent.append(fromBars('error', errorData))
            });
        });
        modal.on('hidden.bs.modal', function (e) {
            variableContent.empty().hide();
            defaultContent.show();
            if (modal.data('mustRefresh')) {
                // If called from big list, reload current tab to make changes
                // visible.
                var tabLabel = $('#ka-biglist-tab-labels').find('.active');
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

// Ajax loading indicator show/hide
$.ajaxSetup({
    beforeSend:function(){
        $(".ajax-loader-container").show();
    },
    complete:function(){
        $(".ajax-loader-container").hide();
    }
});