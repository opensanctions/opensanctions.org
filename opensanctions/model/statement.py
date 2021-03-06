from followthemoney.types import registry
from sqlalchemy import func, Column, Unicode, DateTime, Boolean
from sqlalchemy.dialects.sqlite import insert as insert_sqlite
from sqlalchemy.dialects.postgresql import insert as insert_postgresql


from opensanctions import settings
from opensanctions.model.base import Base, KEY_LEN, VALUE_LEN, db


class Statement(Base):
    """A single statement about a property relevant to an entity.

    For example, this could be useddocker to say: "In dataset A, entity X has the
    property `name` set to 'John Smith'. I first observed this at K, and last
    saw it at L."

    Null property values are not supported. This might need to change if we
    want to support making property-less entities.
    """

    MAX = "max"

    __tablename__ = "statement"

    entity_id = Column(Unicode(KEY_LEN), index=True, primary_key=True)
    prop = Column(Unicode(KEY_LEN), primary_key=True, nullable=False)
    prop_type = Column(Unicode(KEY_LEN), nullable=False)
    schema = Column(Unicode(KEY_LEN), nullable=False)
    value = Column(Unicode(VALUE_LEN), index=True, primary_key=True, nullable=False)
    dataset = Column(Unicode(KEY_LEN), primary_key=True, index=True)
    target = Column(Boolean, default=False, nullable=False)
    unique = Column(Boolean, default=False, nullable=False)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, index=True)

    @classmethod
    def from_entity(cls, entity, unique=False):
        values = []
        for prop, value in entity.itervalues():
            stmt = {
                "entity_id": entity.id,
                "prop": prop.name,
                "prop_type": prop.type.name,
                "schema": entity.schema.name,
                "value": value,
                "dataset": entity.dataset.name,
                "target": entity.target,
                "unique": unique,
                "first_seen": settings.RUN_TIME,
                "last_seen": settings.RUN_TIME,
            }
            values.append(stmt)
        return values

    @classmethod
    def upsert_many(cls, values):
        if not len(values):
            return

        upsert = insert_sqlite
        if db.engine.dialect.name == "postgresql":
            upsert = insert_postgresql

        istmt = upsert(cls.__table__).values(values)
        stmt = istmt.on_conflict_do_update(
            index_elements=["entity_id", "prop", "value", "dataset"],
            set_=dict(
                schema=istmt.excluded.schema,
                prop_type=istmt.excluded.prop_type,
                target=istmt.excluded.target,
                unique=istmt.excluded.unique,
                last_seen=istmt.excluded.last_seen,
            ),
        )
        db.session.execute(stmt)

    @classmethod
    def all_entity_ids(cls, dataset=None, unique=None, target=None, last_seen=MAX):
        q = db.session.query(cls.entity_id)
        if unique is not None:
            q = q.filter(cls.unique == unique)
        if target is not None:
            q = q.filter(cls.target == target)
        if dataset is not None:
            q = q.filter(cls.dataset.in_(dataset.source_names))
        if last_seen == cls.MAX:
            last_seen = cls.max_last_seen(dataset=dataset)
        if last_seen is not None:
            q = q.filter(cls.last_seen == last_seen)
        q = q.distinct()
        return q

    @classmethod
    def all_statements(cls, dataset=None, entity_id=None, last_seen=MAX):
        q = db.session.query(cls)
        if entity_id is not None:
            q = q.filter(cls.entity_id == entity_id)
        if dataset is not None:
            q = q.filter(cls.dataset.in_(dataset.source_names))
        if last_seen == cls.MAX:
            last_seen = cls.max_last_seen(dataset=dataset)
        if last_seen is not None:
            q = q.filter(cls.last_seen == last_seen)
        q = q.order_by(cls.entity_id.asc())
        return q.yield_per(10000)

    @classmethod
    def all_counts(cls, dataset=None, unique=None, target=None, last_seen=MAX):
        q = cls.all_entity_ids(
            dataset=dataset, unique=unique, target=target, last_seen=last_seen
        )
        return q.count()

    @classmethod
    def agg_target_by_country(cls, dataset=None):
        """Return the number of targets grouped by country."""
        count = func.count(func.distinct(cls.entity_id))
        last_seen = cls.max_last_seen(dataset=dataset)
        q = db.session.query(cls.value, count)
        # TODO: this could be generic to type values?
        q = q.filter(cls.target == True)  # noqa
        q = q.filter(cls.prop_type == registry.country.name)
        q = q.filter(cls.last_seen == last_seen)
        if dataset is not None:
            q = q.filter(cls.dataset.in_(dataset.source_names))
        q = q.group_by(cls.value)
        q = q.order_by(count.desc())
        return q.all()

    @classmethod
    def agg_target_by_schema(cls, dataset=None):
        """Return the number of targets grouped by their schema."""
        # FIXME: duplicates entities when there are statements with different schema
        # defined for the same entity.
        count = func.count(func.distinct(cls.entity_id))
        last_seen = cls.max_last_seen(dataset=dataset)
        q = db.session.query(cls.schema, count)
        q = q.filter(cls.target == True)  # noqa
        q = q.filter(cls.last_seen == last_seen)
        if dataset is not None:
            q = q.filter(cls.dataset.in_(dataset.source_names))
        q = q.group_by(cls.schema)
        q = q.order_by(count.desc())
        return q.all()

    @classmethod
    def max_last_seen(cls, dataset=None):
        """Return the latest date of the data."""
        if dataset in settings.DATASET_LAST_SEEN:
            return settings.DATASET_LAST_SEEN[dataset]
        q = db.session.query(func.max(cls.last_seen))
        if dataset is not None:
            q = q.filter(cls.dataset.in_(dataset.source_names))
        for (value,) in q.all():
            settings.DATASET_LAST_SEEN[dataset] = value
            return value

    @classmethod
    def clear(cls, dataset):
        pq = db.session.query(cls)
        # TODO: should this do collections?
        pq = pq.filter(cls.dataset == dataset.name)
        pq.delete(synchronize_session=False)

    def to_dict(self):
        return {
            "entity_id": self.entity_id,
            "prop": self.prop,
            "prop_type": self.prop_type,
            "schema": self.schema,
            "value": self.value,
            "dataset": self.value,
            "target": self.target,
            "unique": self.unique,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }
