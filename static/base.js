var toBeChecked;
var dependencyGraph;

function reduce(seq, start, func) {
    var result = start;
    for (var i = 0; i < seq.length; i++)
        result = func(result, seq[i]);

    return result
}

function wasChecked(checkboxId) {
    /* Checks if a checkbox with id=checkboxId is checked. */
    var selector = 'input[type=checkbox]#' + checkboxId;
    return $(selector).is(':checked')
}

function toggleCheckbox(checkboxId, isChecked) {
    var selector = 'input[type=checkbox]#' + checkboxId;
    $(selector).prop('checked', isChecked)
}

function enableDisableCheckbox(checkboxId, isEnabled) {
    var selector = 'input[type=checkbox]#' + checkboxId;
    $(selector).prop('disabled', !isEnabled);
    if (!isEnabled)
        $(selector).closest('tr').addClass('disabled');
    else
        $(selector).closest('tr').removeClass('disabled')
}

function manageDependencies(serviceId) {
    /* Disable/enable checkboxes for services, when their dependencies are
     * checked or unchecked.
     */
    function walk(currentServiceId) {
        var parentIsChecked = $('input[type=checkbox]#' + currentServiceId)
            .is(':checked');
        var children = dependencyGraph[currentServiceId].children;

        for (var i = 0; i < children.length; i++) {
            var childId = children[i];
            // If checkbox bound to the currentServiceId is unchecked, all its
            // descendants must be unchecked and disabled.
            if (!parentIsChecked) {
                toggleCheckbox(childId, false);
                enableDisableCheckbox(childId, false);
                walk(childId)
            }
            // If checkbox bound to the serviceId is checked, all its children
            // must be enabled, but only if their other parents (if any) are
            // checked too.
            else {
                var parents = dependencyGraph[childId].parents;
                if (reduce(parents, true, function(current, parentId) {
                    return current && wasChecked(parentId);
                }))
                    enableDisableCheckbox(childId, true)
            }
        }
    }

    if (arguments.length == 0)   // on page load
        for (var id in dependencyGraph) {
            if (dependencyGraph.hasOwnProperty(id))
                walk(id);
        }
    else {
        walk(serviceId)
    }
}

function bindCheckboxes() {
///    Bind checkboxes on a page to the dependency management routine.
    $('input[type=checkbox]').on("change", function (event) {
        manageDependencies(event.target.id);
    });
    // Run for the first time to disable checkboxes bound to services with
    // unsatisfied dependencies.
    manageDependencies()
}

if (toBeChecked)
    $(document).ready(function() {
        for (var i = 0; i < toBeChecked.length; i++)
        toggleCheckbox(toBeChecked[i], true);
    });

if (dependencyGraph)
    $(document).ready(bindCheckboxes);

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
