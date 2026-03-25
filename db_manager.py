import couchdb

class CouchDBManager:
    def __init__(self, url, db_name):
        self.server = couchdb.Server(url)
        try:
            self.db = self.server[db_name]
        except couchdb.http.ResourceNotFound:
            self.db = self.server.create(db_name)

    # CREATE
    def create_record(self, data: dict):
        return self.db.save(data)

    # READ (All)
    def read_all(self):
        # Mengambil semua dokumen (kecuali system design docs)
        return [self.db[id] for id in self.db if not id.startswith('_design/')]

    # UPDATE
    def update_record(self, doc_id, updated_data):
        doc = self.db[doc_id]
        # Update field tanpa menghilangkan _id dan _rev
        for key, value in updated_data.items():
            doc[key] = value
        return self.db.save(doc)

    # DELETE
    def delete_record(self, doc_id):
        doc = self.db[doc_id]
        return self.db.delete(doc)