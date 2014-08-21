var toBeChecked;
var dependencyGraph;

function toggleCheckbox($checkbox, isChecked) {
    $checkbox.prop('checked', isChecked);
}

function enableDisableCheckbox($checkbox, isEnabled) {
    $checkbox.prop('disabled', !isEnabled);
    if (!isEnabled)
        $checkbox.closest('tr').addClass('disabled');
    else
        $checkbox.closest('tr').removeClass('disabled')
}

// FIXME: doesn't work for some reason
function manageDependencies(serviceId, isChecked) {
    /* Disable/enable checkboxes for services, when their dependencies are
     * checked or unchecked.
     */
    function walk(currentId, isChecked) {
        dependencyGraph[currentId].checked = isChecked;
        var children = dependencyGraph[currentId].children;

        $.each(dependencyGraph[currentId].children, function(i, childId) {
            // If checkbox bound to the currentId is unchecked, all its
            // descendants must be unchecked and disabled.
            if (!isChecked) {
                dependencyGraph[childId].checked = false;
                dependencyGraph[childId].enabled = false;
                walk(childId, false);
            }
            // If checkbox bound to the serviceId is checked, all its children
            // must be enabled, but only if their other parents (if any) are
            // checked too.
            else {
                var mustEnableChild = true;
                $.each(dependencyGraph[childId].parents, function(parentId) {
                    mustEnableChild = mustEnableChild &&
                        dependencyGraph[parentId].checked
                });
                if (mustEnableChild)
                    dependencyGraph[childId].enabled = true
            }
        });
    }

    // Calculate.
    if (arguments.length == 0)   // on page load
        for (var id in dependencyGraph) {
            if (dependencyGraph.hasOwnProperty(id))
                walk(id, isChecked);
        }
    else {
        walk(serviceId, isChecked)
    }
    var daysTotal = {'days': 0, 'workDays': 0};
    $.each(dependencyGraph, function(key, value) {
        if (value.checked) {
            daysTotal.days += value.days;
            daysTotal.workDays += value.workDays
        }
    });

    // Render.
    $('input[type=checkbox]').each(function() {
        enableDisableCheckbox($(this), dependencyGraph[this.id].enabled);
        toggleCheckbox($(this), dependencyGraph[this.id].checked);
    });
    $('#days-total').text(daysTotal['days']);
    $('#work-days-total').text(daysTotal['workDays'])
}

function bindCheckboxes() {
///    Bind checkboxes on a page to the dependency management routine.
    $('input[type=checkbox]').on("click", function () {
        t = $(this);
        manageDependencies(t.prop('id'), t.is(':checked'));
    });
    // Run for the first time to disable checkboxes bound to services with
    // unsatisfied dependencies.
    manageDependencies()
}

if (dependencyGraph) {
    $(document).ready(bindCheckboxes);
}

/* Here be triggers that rely upon document styling (certain classes
 * absent/present.
 */
$(document).ready(function() {
    var multidescrSrvPlanks = $('.multidescr-srv-plank');

    if (multidescrSrvPlanks.length)  // if spoilers are present on page
        multidescrSrvPlanks.on('click', function() {
            $(this).next().toggle(100)
        })
});
