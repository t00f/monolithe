# -*- coding: utf-8 -*-

import re
import requests
import logging
import time
import sys

from copy import deepcopy

from .printer import Printer
from .factory import VSDKFactory
from .utils import Utils
from unittest import TestCase, TestSuite, TestResult
from collections import OrderedDict

from bambou.config import BambouConfig

HTTP_METHOD_POST = 'POST'
HTTP_METHOD_GET = 'GET'
HTTP_METHOD_DELETE = 'DELETE'
HTTP_METHOD_UPDATE = 'PUT'


IGNORED_ATTRIBUTES = ['id', 'parent_id', 'parent_type', 'creation_date', 'owner', 'last_updated_date', 'last_updated_by']

class TestHelper(object):
    """ Helper to make tests easier

    """
    _vsdk = None
    _debug = False

    @classmethod
    def set_debug_mode(cls, debug=True):
        """ Activate debug mode

        """
        cls._debug = debug

        if cls._debug:
            cls._vsdk.utils.set_log_level(logging.DEBUG)
        else:
            cls._vsdk.utils.set_log_level(logging.ERROR)

    @classmethod
    def use_vsdk(cls, vsdk):
        """ Retain used vsdk

        """
        cls._vsdk = vsdk

    @classmethod
    def current_push_center(cls):
        """ Get current push center

        """
        session = cls._vsdk.NUVSDSession.get_current_session()
        return session.push_center

    @classmethod
    def set_api_key(cls, api_key):
        """ Change api key

        """
        session = cls._vsdk.NUVSDSession.get_current_session()
        session.login_controller.api_key = api_key

    @classmethod
    def session_headers(cls):
        """ Get headers

        """
        session = cls._vsdk.NUVSDSession.get_current_session()
        controller = session.login_controller

        headers = dict()
        headers['Content-Type'] = u'application/json'
        headers['X-Nuage-Organization'] = controller.enterprise
        headers['Authorization'] = controller.get_authentication_header()

        return headers

    @classmethod
    def send_request(cls, method, url, data=None, remove_header=None):
        """ Send request with removed header

        """
        headers = cls.session_headers()

        if remove_header:
            headers.pop(remove_header)

        return requests.request(method=method, url=url, data=data, verify=False, headers=headers)

    @classmethod
    def send_post(cls, url, data, remove_header=None):
        """ Send a POST request

        """
        return cls.send_request(method='post', url=url, data=data, remove_header=remove_header)

    @classmethod
    def send_put(cls, url, data, remove_header=None):
        """ Send a PUT request

        """
        return cls.send_request(method='put', url=url, data=data, remove_header=remove_header)

    @classmethod
    def send_delete(cls, url, data, remove_header=None):
        """ Send a DELETE request

        """
        return cls.send_request(method='delete', url=url, data=data, remove_header=remove_header)

    @classmethod
    def send_get(cls, url, remove_header=None):
        """ Send a GET request

        """
        return cls.send_request(method='get', url=url, remove_header=remove_header)


class _MonolitheTestResult(TestResult):
    """ A TestResult

    """
    def __init__(self):
        """ Initialized a new result

        """
        TestResult.__init__(self)
        self.tests = OrderedDict()

    def getDescription(self, test):
        """ Get test description

        """
        return str(test).split(' ')[0]  # Removing (package.name)

    def addSuccess(self, test):
        """ Add success to the result

        """
        TestResult.addSuccess(self, test)
        self.tests[self.getDescription(test)] = {'status': 'SUCCESS'}

    def addError(self, test, err, connection):
        """ Add error to the result

        """
        TestResult.addError(self, test, err)
        self.tests[self.getDescription(test)] = {'status': 'ERROR', 'stacktrace': err, 'connection': test.last_connection}

    def addFailure(self, test, err, connection):
        """ Add failure to the result

        """
        TestResult.addFailure(self, test, err)
        self.tests[self.getDescription(test)] = {'status': 'FAILURE', 'stacktrace': err, 'connection': test.last_connection}

    def __repr__(self):
        """ Representation

        """
        return "<%s testsRun=%i errors=%i failures=%i>" % \
               (str(self.__class__), self.testsRun, len(self.errors), len(self.failures))


class _MonolitheTestRunner(object):
    """

    """
    def __init__(self):
        """ Initialized """
        pass

    def _makeResult(self):
        """ Return a TestResult implementation

        """
        return _MonolitheTestResult()

    def run(self, test):
        """ Run the given test case or test suite.

        """
        result = self._makeResult()
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime

        run = result.testsRun
        Printer.log("Ran %d test%s in %.3fs" %
                            (run, run != 1 and "s" or "", timeTaken))

        if not result.wasSuccessful():
            Printer.warn("FAILED (failures=%i, errors=%i)" % (len(result.failures), len(result.errors)))
        else:
            Printer.success("OK")
        return result


class _MonolitheTestCase(TestCase):

    _last_connection = None  # Last connection to present errors
    parent = None  # Parent VSD object
    vsdobject = None  # Current VSD object
    user = None  # Current RESTUser

    @property
    def last_connection(self):
        """ Returns last connection """
        return self._last_connection

    @last_connection.setter
    def last_connection(self, connection):
        """ set last_connection """
        self._last_connection = deepcopy(connection)

    # Very Dark Side of unittest... Maybe we should upgrade to unittest2 to do that.
    # Will see that later !
    # CS 05-13-2015
    def run(self, result=None):
        if result is None: result = self.defaultTestResult()
        result.startTest(self)
        testMethod = getattr(self, self._testMethodName)

        try:
            try:
                self.setUp()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info(), self.last_connection)
                return
            ok = False
            try:
                # Printer.log('Running %s' % self._testMethodName)
                testMethod()
                ok = True
            except self.failureException:
                result.addFailure(self, sys.exc_info(), self.last_connection)
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info(), self.last_connection)
            try:
                self.tearDown()
            except KeyboardInterrupt:
                raise
            except:
                result.addError(self, sys.exc_info(), self.last_connection)
                ok = False
            if ok: result.addSuccess(self)
        finally:
            result.stopTest(self)

    def assertErrorEqual(self, errors, title, description, remote_name=u'', index=0):
        """ Check if errors received matches

        """
        self.assertEquals(errors[index]['descriptions'][0]['title'], title)
        self.assertEquals(errors[index]['descriptions'][0]['description'], description)
        self.assertEquals(errors[index]['property'], remote_name)

    def assertConnectionStatus(self, connection, expected_status):
        """ Check if the connection has expected status

        """
        message = self.connection_failure_message(connection, expected_status)
        self.assertEquals(connection.response.status_code, expected_status, message)

    def connection_failure_message(cls, connection, expected_status):
        """ Returns a message that explains the connection status failure """

        return 'Expected status code %s != %s\n' % (expected_status, connection.response.status_code)


class TestMaker(object):
    """ Make tests

    """
    def __init__(self):
        """ Initializes a TestMaker

        """
        self._object_registry = dict()
        self._attributes_registry = dict()

    def register_test(self, function_name, **conditions):
        """ Register test for all attributes

        """
        if function_name not in self._object_registry:
            self._object_registry[function_name] = conditions

    def register_test_for_attribute(self, function_name, **conditions):
        """ Register an attribute test for all given conditions

        """
        if function_name not in self._attributes_registry:
            self._attributes_registry[function_name] = conditions

    def does_attribute_meet_condition(self, attribute, conditions):
        """ Check if the attribute meet all the given conditions

            Args:
                attribute: the attribute information
                conditions: a dictionary of condition to match

            Returns:
                True if the attribute match all conditions. False otherwise
        """
        if conditions is None or len(conditions) == 0:
            return True

        for attribute_name, attribute_value in conditions.iteritems():
            value = getattr(attribute, attribute_name, False)
            if value != attribute_value and bool(value) != attribute_value:
                return False

        return True

    def make_tests(self, vsdobject, testcase):
        """ Make all tests that should be run for the given object in the specified testcase

            Args:
                vsdobject: the vsd object
                testcase: the test case

            Returns:
                It returns a dictionary of all tests to run

        """
        tests = dict()
        attributes = vsdobject.get_attributes()

        for attribute in attributes:

            if attribute.local_name in IGNORED_ATTRIBUTES:
                continue

            for function_name, conditions in self._attributes_registry.iteritems():
                if self.does_attribute_meet_condition(attribute, conditions):
                    (test_name, test_func) = self._create_test(testcase=testcase, vsdobject=vsdobject, function_name=function_name, attribute=attribute)
                    tests[test_name] = test_func

        for function_name, infos in self._object_registry.iteritems():
            (test_name, test_func) = self._create_test(testcase=testcase, vsdobject=vsdobject, function_name=function_name)
            tests[test_name] = test_func

        return tests

    def _create_test(self, testcase, function_name, vsdobject, attribute=None):
        """ Create a test method for the vsdoject

            Args:
                testcase: the testcase to that should manage the method
                function_name: the name of the method in the testcase
                vsdobject: the object that should be tested
                attribute: the attribute information if necessary

            Returns:
                It returns a tuple (name, method) that represents the test method

        """
        func = getattr(testcase, function_name)
        object_name = vsdobject.rest_name

        # Name that will be displayed
        test_name = ''
        rep = dict()
        rep["object"] = object_name

        if attribute:
            rep["attribute"] = attribute.local_name

        rep = dict((re.escape(k), v) for k, v in rep.iteritems())
        pattern = re.compile("|".join(rep.keys()))

        if function_name.startswith('_'):
            function_name = function_name[1:]

        test_name = pattern.sub(lambda m: rep[re.escape(m.group(0))], function_name)

        # Prepare and add test method to test suite
        test_func = None

        if attribute:
            test_func = lambda self, attribute=attribute: func(self, attribute)
        else:
            test_func = lambda self: func(self)

        test_func.__name__ = str(test_name)

        return (test_name, test_func)


##### CREATE TESTS

class CreateTestMaker(TestMaker):
    """ TestCase for create objects

    """
    def __init__(self, parent, vsdobject, user):
        """ Initializes a test case for creating objects

        """
        super(CreateTestMaker, self).__init__()
        self.parent = parent
        self.vsdobject = vsdobject
        self.user = user

        # Object tests
        self.register_test('_test_create_object_with_all_valid_attributes_should_succeed')
        self.register_test('_test_create_object_without_authentication_should_fail')

        # Attribute tests
        self.register_test_for_attribute('_test_create_object_with_required_attribute_as_none_should_fail', is_required=True)
        self.register_test_for_attribute('_test_create_object_with_attribute_not_in_allowed_choices_list_should_fail', has_choices=True)
        self.register_test_for_attribute('_test_create_object_with_attribute_as_none_should_succeed', is_required=False)

    def test_suite(self):
        """ Inject generated tests

        """
        CreateTestCase.parent = self.parent
        CreateTestCase.vsdobject = self.vsdobject
        CreateTestCase.user = self.user

        tests = self.make_tests(vsdobject=self.vsdobject, testcase=CreateTestCase)
        for test_name, test_func in tests.iteritems():
            setattr(CreateTestCase, test_name, test_func)

        return TestSuite(map(CreateTestCase, tests))


class CreateTestCase(_MonolitheTestCase):

    def __init__(self, methodName='runTest'):
        """ Initialize

        """
        _MonolitheTestCase.__init__(self, methodName)
        self.pristine_vsdobject = VSDKFactory.get_instance_copy(self.vsdobject)

    def setUp(self):
        """ Setting up create test

        """
        self.last_connection = None
        self.vsdobject = VSDKFactory.get_instance_copy(self.pristine_vsdobject)

    def tearDown(self):
        """ Clean up environment

        """
        if self.vsdobject and self.vsdobject.id:
            self.vsdobject.delete()
            self.vsdobject.id = None

    # Objects tests
    def _test_create_object_without_authentication_should_fail(self):
        """ Create an object without authentication """

        TestHelper.set_api_key(None)
        (obj, connection) = self.parent.create_child(self.vsdobject)
        self.last_connection = connection

        TestHelper.set_api_key(self.user.api_key)

        self.assertConnectionStatus(connection, 401)

    def _test_create_object_with_all_valid_attributes_should_succeed(self):
        """ Create an object with all its valid attributes should always succeed with 201 response

        """
        (obj, connection) = self.parent.create_child(self.vsdobject)
        self.last_connection = connection

        self.assertConnectionStatus(connection, 201)
        self.assertEquals(obj.to_dict(), self.vsdobject.to_dict())

    # Attributes tests
    def _test_create_object_with_required_attribute_as_none_should_fail(self, attribute):
        """ Create an object with a required attribute as None """

        setattr(self.vsdobject, attribute.local_name, None)
        (obj, connection) = self.parent.create_child(self.vsdobject)
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        self.assertErrorEqual(connection.response.errors, title=u'Invalid input', description=u'This value is mandatory.', remote_name=attribute.remote_name)

    def _test_create_object_with_attribute_as_none_should_succeed(self, attribute):
        """ Create an objet with an attribute as none """

        setattr(self.vsdobject, attribute.local_name, None)
        (obj, connection) = self.parent.create_child(self.vsdobject)
        self.last_connection = connection

        self.assertConnectionStatus(connection, 201)
        # self.assertIsNone(getattr(obj, attribute.local_name), '%s should be none but was %s instead' % (attribute.local_name, getattr(obj, attribute.local_name)))

    def _test_create_object_with_attribute_not_in_allowed_choices_list_should_fail(self, attribute):
        """ Create an object with a wrong choice attribute """

        setattr(self.vsdobject, attribute.local_name, u'A random value')
        (obj, connection) = self.parent.create_child(self.vsdobject)
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        self.assertErrorEqual(connection.response.errors, title=u'Invalid input', description=u'Invalid input', remote_name=attribute.remote_name)


##### UPDATE TESTS

class UpdateTestMaker(TestMaker):
    """ TestCase for updating objects

    """
    def __init__(self, parent, vsdobject, user):
        """ Initializes a test case for updating objects

        """
        super(UpdateTestMaker, self).__init__()
        self.parent = parent
        self.vsdobject = vsdobject
        self.user = user

        # Object tests
        # self.register_test('_test_update_object_with_same_attributes_should_fail')
        # self.register_test('_test_update_object_without_authentication_should_fail')

        # Attribute tests
        # self.register_test_for_attribute('_test_update_object_with_attribute_not_in_allowed_choices_list_should_fail', has_choices=True)
        # self.register_test_for_attribute('_test_update_object_with_required_attribute_as_none_should_fail', is_required=True)
        # self.register_test_for_attribute('_test_update_object_with_attribute_with_choices_as_none_should_fail', has_choices=True)
        # self.register_test_for_attribute('_test_update_object_with_attribute_as_none_should_succeed', is_required=False)

    def test_suite(self):
        """ Inject generated tests

        """
        UpdateTestCase.parent = self.parent
        UpdateTestCase.vsdobject = self.vsdobject
        UpdateTestCase.user = self.user

        tests = self.make_tests(vsdobject=self.vsdobject, testcase=UpdateTestCase)
        for test_name, test_func in tests.iteritems():
            setattr(UpdateTestCase, test_name, test_func)

        return TestSuite(map(UpdateTestCase, tests))


class UpdateTestCase(_MonolitheTestCase):

    def __init__(self, methodName='runTest'):
        """ Initialize

        """
        _MonolitheTestCase.__init__(self, methodName)
        self.pristine_vsdobject = VSDKFactory.get_instance_copy(self.vsdobject)

    def setUp(self):
        """ Setting up create test

        """
        self.last_connection = None
        self.vsdobject = VSDKFactory.get_instance_copy(self.pristine_vsdobject)

        self.parent.create_child(self.vsdobject)

    def tearDown(self):
        """ Clean up environment

        """
        self.vsdobject.delete()

    # Objects tests
    def _test_update_object_without_authentication_should_fail(self):
        """ Update an object without authentication """

        TestHelper.set_api_key(None)
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection
        TestHelper.set_api_key(self.user.api_key)

        self.assertConnectionStatus(connection, 401)

    def _test_update_object_with_same_attributes_should_fail(self):
        """ Update an object with same attributes should always fail with 409 error

        """
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        self.assertErrorEqual(connection.response.errors, title=u'No changes to modify the entity', description=u'There are no attribute changes to modify the entity.')

    # Attributes tests
    def _test_update_object_with_required_attribute_as_none_should_fail(self, attribute):
        """ Update an object with a required attribute as None """

        setattr(self.vsdobject, attribute.local_name, None)
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        self.assertErrorEqual(connection.response.errors, title=u'Invalid input', description=u'This value is mandatory.', remote_name=attribute.remote_name)

    def _test_update_object_with_attribute_with_choices_as_none_should_fail(self, attribute):
        """ Update an objet with an attribute with choices as none should fail """

        setattr(self.vsdobject, attribute.local_name, None)
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        # self.assertIsNone(getattr(obj, attribute.local_name), '%s should be none but was %s instead' % (attribute.local_name, getattr(obj, attribute.local_name)))

    def _test_update_object_with_attribute_not_in_allowed_choices_list_should_fail(self, attribute):
        """ Update an object with a wrong choice attribute """

        setattr(self.vsdobject, attribute.local_name, u'A random value')
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection

        self.assertConnectionStatus(connection, 409)
        self.assertErrorEqual(connection.response.errors, title=u'Invalid input', description=u'Invalid input', remote_name=attribute.remote_name)

    def _test_update_object_with_attribute_as_none_should_succeed(self, attribute):
        """ Update an objet with an attribute as none """

        setattr(self.vsdobject, attribute.local_name, None)
        (obj, connection) = self.vsdobject.save()
        self.last_connection = connection

        self.assertConnectionStatus(connection, 200)
        self.assertIsNone(getattr(obj, attribute.local_name), '%s should be none but was %s instead' % (attribute.local_name, getattr(obj, attribute.local_name)))


class TestsRunner(object):
    """ Runner for VSD Objects tests

    """
    def __init__(self, vsdurl, username, password, enterprise, version, model, parent_resource=None, parent_id=None, **default_values):
        """ Initializes the TestsRunner.

            Args:
                vsdurl (string): the vsd url
                username (string): the username to connect with
                password (string): the password for the username
                enterprise (string): the enterprise
                version (float): the vsd api version (eg 3.2)
                model (Model): the model representation of the object to test
                parent_resource: the parent_resource if necessary
                parent_id: the parent id if necessary
                default_values: all default values to have a valid version of the model

        """
        VSDKFactory.init(version)
        vsdk = VSDKFactory.get_vsdk_package()
        TestHelper.use_vsdk(vsdk)

        session = vsdk.NUVSDSession(api_url=vsdurl, username=username, password=password, enterprise=enterprise, version=version)
        session.start()

        self.user = session.user
        self.resource_name = model.resource_name

        python_attributes = {Utils.get_python_name(name): value for name, value in default_values.iteritems()}
        self.vsdobject = VSDKFactory.get_instance_from_model(model, **python_attributes)

        self.parent = None

        if parent_resource and parent_id:
            try:
                self.parent = VSDKFactory.get_instance(parent_resource, id=parent_id)
                self.parent.fetch()
            except:
                Printer.raiseError('Could not find parent %s with ID=%s' % (parent_resource, parent_id))

        VSDKFactory.update_fetchers_for_object(self.parent, self.vsdobject, model)

        self.is_create_allowed = False
        self.is_delete_allowed = False
        self.is_get_allowed = False
        self.is_get_all_allowed = False
        self.is_update_allowed = False

        for path, api in model.apis['parents'].iteritems():
            for operation in api.operations:
                method = operation.method
                if method == HTTP_METHOD_POST:
                    self.is_create_allowed = True
                elif method == HTTP_METHOD_GET:
                    self.is_get_all_allowed = True
                    self.is_get_allowed = True
                elif method == HTTP_METHOD_UPDATE:
                    self.is_update_allowed = True
                elif method == HTTP_METHOD_DELETE:
                    self.is_delete_allowed = True

    def test_suite(self):
        """ Returns a TestSuite that can be run

            TestSuite is computed according to what is defined in the model

        """
        all_suites = TestSuite()
        if self.is_create_allowed:
            maker = CreateTestMaker(self.parent, self.vsdobject, self.user)
            suite = maker.test_suite()
            all_suites.addTests(suite)

        if self.is_update_allowed:
            maker = UpdateTestMaker(self.parent, self.vsdobject, self.user)
            suite = maker.test_suite()
            all_suites.addTests(suite)

        # Do the same of update and delete.. and combine suites

        return all_suites

    def run(self):
        """ Runs all tests on the specified VSD

        """
        BambouConfig.set_should_raise_bambou_http_error(False)
        TestHelper.set_debug_mode(False)

        suite = self.test_suite()
        results = _MonolitheTestRunner().run(suite)

        TestHelper.set_debug_mode(False)
        BambouConfig.set_should_raise_bambou_http_error(True)

        return results
