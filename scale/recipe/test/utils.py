"""Defines utility methods for testing jobs and job types"""
from __future__ import unicode_literals

import django.utils.timezone as timezone

import job.test.utils as job_test_utils
import trigger.test.utils as trigger_test_utils
from recipe.configuration.definition.recipe_definition import RecipeDefinition
from recipe.configuration.data.recipe_data import RecipeData
from recipe.configuration.data.exceptions import InvalidRecipeConnection
from recipe.handlers.graph import RecipeGraph
from recipe.handlers.graph_delta import RecipeGraphDelta
from recipe.models import Recipe, RecipeJob, RecipeType, RecipeTypeRevision
from recipe.triggers.configuration.trigger_rule import RecipeTriggerRuleConfiguration
from trigger.handler import TriggerRuleHandler, register_trigger_rule_handler


NAME_COUNTER = 1
VERSION_COUNTER = 1
TITLE_COUNTER = 1
DESCRIPTION_COUNTER = 1


MOCK_TYPE = 'MOCK_RECIPE_TRIGGER_RULE_TYPE'
MOCK_ERROR_TYPE = 'MOCK_RECIPE_TRIGGER_RULE_ERROR_TYPE'


class MockTriggerRuleConfiguration(RecipeTriggerRuleConfiguration):
    """Mock trigger rule configuration for testing
    """

    def __init__(self, trigger_rule_type, configuration):
        super(MockTriggerRuleConfiguration, self).__init__(trigger_rule_type, configuration)

    def validate(self):
        pass

    def validate_trigger_for_job(self, job_interface):
        return []

    def validate_trigger_for_recipe(self, recipe_definition):
        return []


class MockErrorTriggerRuleConfiguration(RecipeTriggerRuleConfiguration):
    """Mock error trigger rule configuration for testing
    """

    def __init__(self, trigger_rule_type, configuration):
        super(MockErrorTriggerRuleConfiguration, self).__init__(trigger_rule_type, configuration)

    def validate(self):
        pass

    def validate_trigger_for_job(self, job_interface):
        return []

    def validate_trigger_for_recipe(self, recipe_definition):
        raise InvalidRecipeConnection('Error!')


class MockTriggerRuleHandler(TriggerRuleHandler):
    """Mock trigger rule handler for testing
    """

    def __init__(self):
        super(MockTriggerRuleHandler, self).__init__(MOCK_TYPE)

    def create_configuration(self, config_dict):
        return MockTriggerRuleConfiguration(MOCK_TYPE, config_dict)


class MockErrorTriggerRuleHandler(TriggerRuleHandler):
    """Mock error trigger rule handler for testing
    """

    def __init__(self):
        super(MockErrorTriggerRuleHandler, self).__init__(MOCK_ERROR_TYPE)

    def create_configuration(self, config_dict):
        return MockErrorTriggerRuleConfiguration(MOCK_ERROR_TYPE, config_dict)


register_trigger_rule_handler(MockTriggerRuleHandler())
register_trigger_rule_handler(MockErrorTriggerRuleHandler())


def create_recipe_type(name=None, version=None, title=None, description=None, definition=None, trigger_rule=None):
    """Creates a recipe type for unit testing

    :returns: The RecipeType model
    :rtype: :class:`recipe.models.RecipeType`
    """

    if not name:
        global NAME_COUNTER
        name = 'test-recipe-type-%i' % NAME_COUNTER
        NAME_COUNTER += 1

    if not version:
        global VERSION_COUNTER
        version = '%i.0.0' % VERSION_COUNTER
        VERSION_COUNTER += 1

    if not title:
        global TITLE_COUNTER
        title = 'Test Recipe Type %i' % TITLE_COUNTER
        TITLE_COUNTER += 1

    if not description:
        global DESCRIPTION_COUNTER
        description = 'Test Description %i' % DESCRIPTION_COUNTER
        DESCRIPTION_COUNTER += 1

    if not definition:
        definition = {
            'version': '1.0',
            'input_data': [],
            'jobs': [],
        }

    if not trigger_rule:
        trigger_rule = trigger_test_utils.create_trigger_rule()

    recipe_type = RecipeType()
    recipe_type.name = name
    recipe_type.version = version
    recipe_type.title = title
    recipe_type.description = description
    recipe_type.definition = definition
    recipe_type.trigger_rule = trigger_rule
    recipe_type.save()

    RecipeTypeRevision.objects.create_recipe_type_revision(recipe_type)

    return recipe_type


def edit_recipe_type(recipe_type, definition):
    """Updates the definition of a recipe type, including creating a new revision for unit testing
    """
    RecipeType.objects.edit_recipe_type(recipe_type.id, None, None, RecipeDefinition(definition), None, False)


def create_recipe(recipe_type=None, data=None, event=None, is_superseded=False, superseded=None):
    """Creates a recipe for unit testing

    :returns: The recipe model
    :rtype: :class:`recipe.models.Recipe`
    """

    if not recipe_type:
        recipe_type = create_recipe_type()
    if not data:
        data = {}
    if not event:
        event = trigger_test_utils.create_trigger_event()
    if is_superseded and not superseded:
        superseded = timezone.now()

    recipe = Recipe()
    recipe.recipe_type = recipe_type
    recipe.recipe_type_rev = RecipeTypeRevision.objects.get_revision(recipe_type.id, recipe_type.revision_num)
    recipe.event = event
    recipe.data = data
    recipe.is_superseded = is_superseded
    recipe.superseded = superseded
    recipe.save()

    return recipe


def create_recipe_job(recipe=None, job_name=None, job=None):
    """Creates a job type model for unit testing

    :param recipe: The associated recipe
    :type recipe: :class:'recipe.models.Recipe'
    :param job_name: The associated name for the recipe job
    :type job_name: string
    :param job: The associated job
    :type job: :class:'job.models.Job'
    :returns: The recipe job model
    :rtype: :class:`recipe.models.RecipeJob`
    """
    if not recipe:
        recipe = create_recipe()

    if not job_name:
        job_name = 'Test Job Name'

    if not job:
        job = job_test_utils.create_job()

    recipe_job = RecipeJob()
    recipe_job.job_name = job_name
    recipe_job.job = job
    recipe_job.recipe = recipe
    recipe_job.save()
    return recipe_job


def create_recipe_handler(recipe_type=None, data=None, event=None, superseded_recipe=None, delta=None,
                          superseded_jobs=None):
    """Creates a recipe along with its declared jobs for unit testing

    :returns: The recipe handler with created recipe and jobs
    :rtype: :class:`recipe.handlers.handler.RecipeHandler`
    """

    if not recipe_type:
        recipe_type = create_recipe_type()
    if not data:
        data = {}
    if not isinstance(data, RecipeData):
        data = RecipeData(data)
    if not event:
        event = trigger_test_utils.create_trigger_event()
    if superseded_recipe and not delta:
        delta = RecipeGraphDelta(RecipeGraph(), RecipeGraph())

    return Recipe.objects.create_recipe(recipe_type, data, event, superseded_recipe=superseded_recipe,
                                        delta=delta, superseded_jobs=superseded_jobs)
