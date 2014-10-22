# -*- coding: utf-8 -*-

from bambou import NURESTFetcher


class NUTCAsFetcher(NURESTFetcher):
    """ TCA fetcher """

    @classmethod
    def managed_class(cls):
        """ Managed class """

        from .. import NUTCA
        return NUTCA