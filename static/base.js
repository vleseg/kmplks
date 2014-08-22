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

// FIXME: find out, why doesn't it work
function generateActivePaths() {
    function recursiveHelper(currentNode, currentPath) {
        if (currentNode.enabled) {
            currentPath.push(currentNode);
            if (currentPath.children.length > 0)
                $.each(currentPath.children, function(i, child) {
                    recursiveHelper(child, currentPath)
                });
            else
                activePaths.push(currentPath)
        }
    }
    var activePaths = [];
    var parentNodes = [];
    $.each(dependencyGraph, function(key, value) {
        if (value.parents.length == 0)
            parentNodes.push(key)
    });
    $.each(parentNodes, function(i, node) {
        recursiveHelper(node, [])
    });

    return activePaths
}

function calculateNewTotal(path) {
    var total = {'days': 0, 'workDays': 0};
    $.each(path, function (i, node) {
        total.days += node.days;
        total.workDays += node.workDays
    });

    return total
}

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
                $.each(dependencyGraph[childId].parents, function(i, parentId) {
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
                walk(id, false);
        }
    else {
        walk(serviceId, isChecked)
    }
    var totalDays = {'days': 0, 'workDays': 0};
    $.each(generateActivePaths(), function(i, path) {
        var newTotal = calculateNewTotal(path);
        if (newTotal.days + newTotal.workDays >
                totalDays.days + totalDays.workDays)
            totalDays = newTotal
    });

    // Render.
    $('input[type=checkbox]').each(function() {
        enableDisableCheckbox($(this), dependencyGraph[this.id].enabled);
        toggleCheckbox($(this), dependencyGraph[this.id].checked);
    });
    $('#days-total').text(totalDays['days']);
    $('#work-days-total').text(totalDays['workDays'])
}

function bindCheckboxes() {
///    Bind checkboxes on a page to the dependency management routine.
    $('input[type=checkbox]').on("click", function () {
        var id = $(this).prop('id');
        // Current state of 'checked' must be reversed for this i.
        manageDependencies(id, !dependencyGraph[id].checked);
    });
}

if (dependencyGraph) {
    $(document).ready(function() {
        bindCheckboxes();
        // Run for the first time to disable checkboxes bound to services with
        // unsatisfied dependencies.
        manageDependencies()
    });
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
