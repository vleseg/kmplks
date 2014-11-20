function FieldsRenderingRules() {
    this.slots = {
        'int': 1, 'ref': 1, 'multi_ref': 1, 'repr': 1, 'bool': 1, 'enum': 1,
        'plain': 2, 'rich': 2
    };
}

var FRR = new FieldsRenderingRules();

function fetchFields(action, toFetch, renderFn, errorMsgCntr) {
    /* Wrapper around fields of entity fetching API request. */
    var uriFragment;

    if (action == 'edit')
        // toFetch is the urlsafe entity id
        uriFragment = 'entities/' + toFetch;
    else if (action == 'new')
        // toFetch is the name of a kind
        uriFragment = toFetch + '/fields';
    else
        throw new Error("Invalid action type: " + action);

    $.getJSON('/admin/api/' + uriFragment, renderFn)
        .fail(function (xhr, status, error) {
            renderErrorMsg(errorMsgCntr, status, error)
        })
}

function renderField(field, slotsRequired) {
    /* Render entity property fetched via API request as HTML form field(s). */
    var templateName = field.type.replace(/_/g, '-');
    var fieldId = 'ka-' + field.name + '-field';
    // Render label for form field(s).
    var labelHTML = fromBars('label', {
        'fieldId': fieldId,
        'labelText': field.label
    });

    // Render form field(s).
    var fieldHTML = fromBars(templateName, field);

    // Combine rendered form field(s) and its label.
    var compiled = $(fromBars('field-container', {
        'labelHTML': labelHTML, 'fieldHTML': fieldHTML,
        'isNarrow': slotsRequired == 1, 'fieldId': fieldId
    }));

    // Select fields have to be populated with options.
    if (field.type == 'enum' || field.type == 'bool')
        compiled.find('select').val(field.value.toString());

    return compiled
}

$(document).ready(function() {
    var entityEditForm = $('#ka-edit-form');
    if (entityEditForm.length > 0) {
        var action = entityEditForm.data('action');
        var toFetch = entityEditForm.data('toFetch');

        fetchFields(action, toFetch, function (data) {
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
        }, entityEditForm);

        // Save changes to entity on submit.
        entityEditForm.submit(function () {

        });

        // Close window on 'Cancel' button click.
        $('#ka-edit-close-btn').click(function () {
            window.close()
        })
    }
});