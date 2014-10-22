# -*- coding: utf-8 -*-

from bambou import NURESTFetcher


class NUVSDComponentsFetcher(NURESTFetcher):
    """ VSDComponent fetcher """

    @classmethod
    def managed_class(cls):
        """ Managed class """

        from .. import NUVSDComponent
        return NUVSDComponent