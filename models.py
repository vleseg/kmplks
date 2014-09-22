# coding=utf-8
# TODO: update UML schema and description in Evernote correspondingly
from __future__ import unicode_literals
from sys import modules
# Third-party imports
from google.appengine.ext import ndb
# Project-specific imports
from config import CFG


class KompleksModelError(BaseException):
    pass


class BaseModel(ndb.Model):
    """
    Base class for models in Kompleks app. Inherit new models from it.

    _name: Verbose name of the model to be used in user interface, two-element
        tuple. First element is singular form, second is plural.
    _repr_field: Property, which value will be used as representation of the
        entity (i. e. human-readable primary key).
    """
    # Meta
    _name = None
    _repr_field = None

    id = ndb.IntegerProperty(required=True)

    @classmethod
    def iter_property_names(cls, exclude=None):
        for prop in cls._properties:
            if exclude is not None and prop not in exclude:
                yield prop

    def as_tuple(self, *args):
        result = []

        for arg in args:
            if arg == '_urlsafe':
                result.append(self.urlsafe())
            else:
                result.append(getattr(self, arg))

        return result

    def urlsafe(self):
        return self.key.urlsafe()


class DocClass(BaseModel):
    """
    A class of a document.

    Purpose of a document, issuing OGV, it's nature or any other trait, that
    may serve as a unifying characteristic for a set of documents.
    """
    # Meta
    _name = (u'Класс документа', u'Классы документов')
    _repr_field = 'value'

    value = ndb.StringProperty(required=True, verbose_name=u'Значение')
    sort_key = ndb.IntegerProperty(
        required=True, verbose_name=u'Ключ сортировки')


class MFC(BaseModel):
    """
    A multifunctional center for delivery of public services.

    MFCs deliver public services, including those united in komplekses.

    name: Name of the MFC. Must always include name of the city (town,
        village), where MFC operates, so that RCTO operator could always tell
        if a caller is able to apply for a kompleks in his/her area.
    """
    # Meta
    _name = (u'МФЦ', u'МФЦ')
    _repr_field = 'name'

    name = ndb.StringProperty(required=True, verbose_name="Название")


class OGV(BaseModel):
    """
    A state agency.

    State agencies deliver public services (sometimes via MFCs).

    name: Name of the OGV. This property must store OVG's official name as
        defined by laws and other regulative acts.
    short_name: Abbreviation of OGV's official name. This property must store a
        shortening, well-known among common people.
    """
    # Meta
    _name = (u'Ведомство', u'Ведомства')
    _repr_field = 'name'

    name = ndb.StringProperty(required=True, verbose_name=u"Полное название")
    short_name = ndb.StringProperty(required=True, verbose_name=u'Сокращение')


class Kompleks(BaseModel):
    """
    A set of simultaneously delivered public services.

    A compound entity, which consists of both synchronously and asynchronously
    delivered public services and is semantically bound with a specific life
    situation (i. e. child birth, name change) or specific citizen category
    (i. e. labour veterans, long families). A citizen is free to exclude
    services from the kompleks when applying unless there are dependencies
    present (see: Service.dependencies and Service.prerequisite_description)

    name: Name of the kompleks. It usually coincides with a corresponding life
        situation or a citizen category.
    mfcs: MFCs, where the kompleks is available.
    """
    # Meta
    _name = (u'Комлпексная услуга', u'Комплексные услуги')
    _repr_field = 'name'

    name = ndb.StringProperty(required=True, verbose_name=u'Название')

    # Relationships
    mfcs = ndb.KeyProperty(
        MFC, repeated=True,
        verbose_name=u"В каких МФЦ доступна комплесная услуга?"
    )


class Service(BaseModel):
    """
    A public service.

    Public service is an activity of a state or a municipal agency, which is
    conducted on citizen's request: registering birth, issuing a passport etc.
    Public services can be outsourced (to some extent) to MFCs. All services in
    this app are delivered by MFCs.

    name: Name of the service. May not necessarily be exactly as defined by
        regulative acts, but it must be recognizable for RCTO operator.
    short_description: Brief description of who can apply for the service.
    kb_id: id of the service in MFC knowledge base. It is used to form a link
        when corresponding page is rendered.
    prerequisite_description: Brief description of a situation in which the
        service is considered a satisfied dependency (only required if the
        service is a sine qua non for some other service)
    max_days: Calendar days required to deliver the service.
    work_days: Working days required to deliver the service. max_days and
        work_days may be combined in a service.
    terms_description: Brief description of how service's deadline may shift
        due to various factors (optional).

    ogv: OGV, which is responsible for delivering the service
    containing_komplekses: Komplekses, that include the service.
    related_komplekses: Komplekses, that are coherent to the service
        (optional). Sometimes a service suits perfectly to citizen's life
        situation, but, for some reason, is not included into a corresponding
        kompleks. The concept of 'related services' alleviates this piece of
        injustice. Take note, however, that since related services are not part
        of kompleks, a citizen will have to apply for them separately.
    dependencies: Other services that are sine qua non for the service. They
        can be omitted only if a condition described in
        prerequisite_description is met.
    """
    # Meta
    _name = (u'Услуга', u'Услуги')
    _repr_field = 'name'

    name = ndb.StringProperty(required=True, verbose_name=u'Название')
    short_description = ndb.TextProperty(
        required=True, verbose_name=u'Краткое описание')
    kb_id = ndb.IntegerProperty(
        required=True, verbose_name=u'ID в Базе знаний МФЦ')
    prerequisite_description = ndb.StringProperty(
        verbose_name=u'При каком условии надобность в услуге отпадает?')
    max_days = ndb.IntegerProperty(
        required=True, verbose_name=u'Максимальный срок (календарные дни)')
    max_work_days = ndb.IntegerProperty(
        required=True, verbose_name=u'Максимальный срок (рабочие дни)')
    terms_description = ndb.StringProperty(
        verbose_name=u'Примечание к срокам предоставления услуги')

    # Relationships
    ogv = ndb.KeyProperty(
        OGV, required=True, verbose_name=u'Ответственное ведомство')
    containing_komplekses = ndb.KeyProperty(
        Kompleks, repeated=True,
        verbose_name=u'Комплексы, в которые входит услуга'
    )
    related_komplekses = ndb.KeyProperty(
        Kompleks, repeated=True,
        verbose_name=u'Комплексы, к которым услугу можно отнести'
    )
    dependencies = ndb.KeyProperty(
        kind="Service", repeated=True,
        verbose_name="Какие услуги нужно получить предварительно?"
    )


class Document(BaseModel):
    """
    A necessary document, provided by a citizen to apply for a service.

    Documents contain information required by OGV's to deliver a service and
    ascertain citizen's rights to apply for a service. They may take shape of a
    paper document or constitute an abstract entity -- effectively a collection
    of data.

    name: Name of the document.
    description: Brief or verbose description of conditions, under which this
        document must be provided, its obligatoriness and other useful
        information. If document is a fillable form, description should also
        include a brief form specification. Descriptions are stores as
        serialized XHTML.
    o_count_method, c_count_method: Method of counting of the document's
        originals (copies) to be used, when the result list is compiled. See
        comments to the COUNT_METHOD constant for more information.
    o_supply_type: Generic designation of what usually happens with the
        original document. See the ORIGINAL_SUPPLY_TYPE constant for more
        information. This property may be overridden by a bound
        DocumentToService instance.
    n_originals, n_copies: Generic number of originals and copies of the
        document, usually expected from a citizen, who is applying for the
        service, where the document is required. This property may be
        overridden by a bound DocumentToService instance.
    is_a_paper_document: Designation of whether this document has a physical
        (paper) form.

    doc_class: Class of the document.
    """
    # Meta
    _name = (u'Документ', u'Документы')
    _repr_field = 'name'

    name = ndb.StringProperty(required=True)
    description = ndb.TextProperty(
        default=u'Предоставляется в любом случае',
        verbose_name=u'Условия предоставления'
    )
    o_count_method = ndb.StringProperty(
        default='one_for_all', choices=CFG['COUNT_METHOD'].keys(),
        verbose_name=u'Метод подсчета оригиналов'
    )
    c_count_method = ndb.StringProperty(
        default='per_service', choices=CFG['COUNT_METHOD'].keys(),
        verbose_name=u'Метод подсчета копий'
    )
    o_supply_type = ndb.StringProperty(
        default='demonstrate', choices=CFG['ORIGINAL_SUPPLY_TYPE'].keys(),
        verbose_name=u'Возвращается ли оригинал заявителю?'
        )
    n_originals = ndb.IntegerProperty(default=1, verbose_name=u'Оригиналы')
    n_copies = ndb.IntegerProperty(default=1, verbose_name=u'Копии')
    is_a_paper_document = ndb.BooleanProperty(
        default=True, verbose_name=u'Это физический документ?')
    doc_class = ndb.KeyProperty(
        DocClass, required=True, verbose_name="Класс документа")

    def precompile_description(self, dts_items):
        """
        Precompiles a description of the document to be shown on the result
        list.

        Result of compilation heavily depends on the number of dts_items,
        values of their 'description' properties and values of their
        'override_description' properties.

        :type dts_items: list[DocumentToService]
        :returns: Either a dictionary with keys 'from_doc' and 'from_dts' or a
            list of such dictionaries
        :rtype: dict[str, str | NoneType] |
                list[dict[str, str | str | NoneType]]
        """
        def _compile_single(_dts, _result):
            if _dts.description is None:
                _result['from_doc'] = self.description
            elif _dts.override_description:
                _result['from_dts'] = _dts.description
            else:
                _result['from_doc'] = self.description
                _result['from_dts'] = _dts.description

        result = {'from_doc': None, 'from_dts': None}

        if len(dts_items) == 1:
            dts = dts_items[0]
            _compile_single(dts, result)
        else:
            # If no description was specified for any of the DocumentToService
            # entities.
            if all(dts.description is None for dts in dts_items):
                result["from_doc"] = self.description
            # If all descriptions in DocumentToService entities are identical.
            elif len(set(dts.description for dts in dts_items)) == 1:
                result['from_dts'] = dts_items[0].description
            else:
                result = []
                for dts in dts_items:
                    result_item = {}
                    _compile_single(dts, result_item)
                    result_item['service'] = dts.service.get()
                    result.append(result_item)

        return result

    def count_up(self, what, dts_items):
        """
        Count up originals or copies of the document for result list taking in
        account all DocumentToService instances provided and own o_count_method
        and c_count_method properties.

        :param str what: 'originals' or 'copies'
        :type dts_items: list[DocumentToService]
        """
        if what == 'originals':
            count_method, attr_name = self.o_count_method, "n_originals"
        else:  # what == 'copies'
            count_method, attr_name = self.c_count_method, "n_copies"
        total = 0

        if count_method == 'one_for_all':
            total = 1
        elif count_method == 'per_service':
            for dts in dts_items:
                # Get n from DocumentToService entity...
                current_n = getattr(dts, attr_name)
                # ...or from Document if former was not defined.
                total += current_n if current_n else getattr(self, attr_name)
        else:  # count_method == 'per_ogv'
            unique_ogv_names = set(dts.service.get().ogv.get().name
                                   for dts in dts_items)
            total = getattr(self, attr_name) * len(unique_ogv_names)

        return total

    def define_o_supply_type(self, dts_items):
        """
        Define, what actually happens with original document before result list
        is compiled.

        Simply returns the strongest o_supply_type property value, defined in
        the document and all bound DocumentToService entities. Strength is
        already defined in ORIGINAL_SUPPLY_TYPE constant: the further to the
        right, the stronger.

        :type dts_items: list[DocumentToService]
        """
        ost = CFG['ORIGINAL_SUPPLY_TYPE']

        # Gathering together o_supply_type property values from Document and
        # its bound DocumentToService entities.
        o_supply_types = [
            dts.o_supply_type for dts in dts_items if dts.o_supply_type]
        o_supply_types.append(self.o_supply_type)

        rank_ost = lambda s: ost.index(s)
        strongest_ost = max(o_supply_types, key=rank_ost)

        return ost[strongest_ost]


class DocumentToService(BaseModel):
    """
    A relation between a document and a service.

    Qualifying standards for a document may change from service to service.
    These changes are reflected by this model's attributes.

    description: Modification of a value of Document.description.
    n_originals, n_copies: Number of originals (copies) actually required from
        a citizen applying for a specific service (optional; if not defined,
        value of Document.n_originals / Document.n_copies is used). If
        Document.o_count_type (Document.c_count_type) is 'one_for_all' or
        'per_ogv' this property must be left undefined.
    o_supply_type: Designation of what actually happens with an original
        document in a specific service (optional; if not defined, value of
        Document.o_supply_type is used).
    override_description: Designation of whether Document.description must be
        overridden or appended.

    document: A document, that is being linked to a service.
    service: A service, that is being linked to a document.
    kompleks: A kompleks, that is being linked to a document-to-service
        relation (optional). A document is excluded from result list if this
        property is defined and user chooses another kompleks (not the one
        referenced by this property) at runtime.
    """
    description = ndb.TextProperty()
    n_originals = ndb.IntegerProperty()
    n_copies = ndb.IntegerProperty()
    o_supply_type = ndb.StringProperty(choices=CFG[
        'ORIGINAL_SUPPLY_TYPE'].keys())
    override_description = ndb.BooleanProperty(default=False)

    # Relations
    document = ndb.KeyProperty(Document, required=True)
    service = ndb.KeyProperty(Service, required=True)
    kompleks = ndb.KeyProperty(Kompleks)

this_module = modules[__name__]


def from_urlsafe(urlsafe, multi=False, key_only=False):
    if multi:
        return [from_urlsafe(e, key_only=key_only) for e in urlsafe]
    if key_only:
        return ndb.Key(urlsafe=urlsafe)
    return ndb.Key(urlsafe=urlsafe).get()


def iter_datastore_kinds():
    for name in this_module.__dict__:
        obj = getattr(this_module, name)
        try:
            if issubclass(obj, BaseModel) and obj is not BaseModel:
                yield obj
        except TypeError:  # current object is not a class
            pass


def get_kind(raw_kind):
    if isinstance(raw_kind, (str, unicode)):
        try:
            return getattr(this_module, raw_kind)
        except AttributeError:
            raise KompleksModelError(
                "Entity kind does not exist: '{}'".format(raw_kind))
    else:  # a kind as-is
        return raw_kind