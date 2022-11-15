<template>
  <v-dialog v-model="showCreate" persistent max-width="800px">
    <template v-slot:activator="{ on }">
      <v-btn icon v-on="on">
        <v-icon>add</v-icon>
      </v-btn>
    </template>
    <v-card>
      <v-card-title>
        <span class="headline">Create Search Filter</span>
      </v-card-title>
      <v-stepper v-model="step">
        <v-stepper-header>
          <v-stepper-step :complete="step > 1" step="1" editable> Filter </v-stepper-step>
          <v-divider />

          <v-stepper-step :complete="step > 2" step="2" editable> Preview </v-stepper-step>
          <v-divider />

          <v-stepper-step step="3" editable> Save </v-stepper-step>
        </v-stepper-header>

        <v-stepper-items>
          <v-stepper-content step="1">
            <v-card>
              <v-card-text>
                <v-tabs color="primary" right>
                  <v-tab>Basic</v-tab>
                  <v-tab>Advanced</v-tab>
                  <v-tab-item>
                    <v-list dense>
                      <v-list-item>
                        <v-list-item-content>
                          <tag-filter-auto-complete
                            :project="searchFilter.project"
                            v-model="searchFilter.filters.tag"
                            label="Tags"
                          />
                        </v-list-item-content>
                      </v-list-item>
                      <v-list-item>
                        <v-list-item-content>
                          <tag-type-filter-combobox
                            :project="searchFilter.project"
                            v-model="searchFilter.filters.tag_type"
                            label="Tag Types"
                          />
                        </v-list-item-content>
                      </v-list-item>
                      <v-list-item>
                        <v-list-item-content>
                          <case-type-combobox
                            :project="searchFilter.project"
                            v-model="searchFilter.filters.case_type"
                          />
                        </v-list-item-content>
                      </v-list-item>
                      <v-list-item>
                        <v-list-item-content>
                          <case-priority-combobox
                            :project="searchFilter.project"
                            v-model="searchFilter.filters.case_priority"
                          />
                        </v-list-item-content>
                      </v-list-item>
                      <v-list-item>
                        <v-list-item-content>
                          <case-status-multi-select v-model="searchFilter.filters.status" />
                        </v-list-item-content>
                      </v-list-item>
                      <v-list-item>
                        <v-list-item-content>
                          <v-select
                            :items="visibilities"
                            v-model="searchFilter.filters.visibility"
                            name="visibility"
                            item-text="name"
                            return-object
                            label="Visibility"
                          />
                        </v-list-item-content>
                      </v-list-item>
                    </v-list>
                  </v-tab-item>
                  <v-tab-item>
                    <div style="height: 400px">
                      <MonacoEditor
                        v-model="searchFilter.expression_str"
                        :options="editorOptions"
                        language="json"
                      ></MonacoEditor>
                    </div>
                  </v-tab-item>
                </v-tabs>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn @click="closeCreateDialog()" text> Cancel </v-btn>
                <v-btn color="info" @click="step = 2"> Continue </v-btn>
              </v-card-actions>
            </v-card>
          </v-stepper-content>

          <v-stepper-content step="2">
            <v-card>
              <v-card-text>
                Examples matching your filter:
                <v-data-table
                  hide-default-footer
                  :headers="previewFields"
                  :items="previewRows.items"
                  :loading="previewRowsLoading"
                >
                  <template v-slot:item.case_priority.name="{ item }">
                    <case-priority :priority="item.case_priority.name" />
                  </template>
                  <template v-slot:item.status="{ item }">
                    <case-status :status="item.status" :id="item.id" />
                  </template>
                </v-data-table>
              </v-card-text>
              <v-card-actions>
                <v-spacer />
                <v-btn @click="closeCreateDialog()" text> Cancel </v-btn>
                <v-btn color="info" @click="step = 3" :loading="loading"> Continue </v-btn>
              </v-card-actions>
            </v-card>
          </v-stepper-content>
          <v-stepper-content step="3">
            <ValidationObserver disabled v-slot="{ invalid, validated }">
              <v-card>
                <v-card-text>
                  Provide a name and description for your filter.
                  <ValidationProvider name="Name" rules="required" immediate>
                    <v-text-field
                      v-model="searchFilter.name"
                      label="Name"
                      hint="A name for your saved search."
                      slot-scope="{ errors, valid }"
                      :error-messages="errors"
                      :success="valid"
                      clearable
                      required
                    />
                  </ValidationProvider>
                  <ValidationProvider name="Description" rules="required" immediate>
                    <v-textarea
                      v-model="searchFilter.description"
                      label="Description"
                      hint="A short description."
                      slot-scope="{ errors, valid }"
                      :error-messages="errors"
                      :success="valid"
                      clearable
                      auto-grow
                      required
                    />
                  </ValidationProvider>
                </v-card-text>
                <v-card-actions>
                  <v-spacer />
                  <v-btn @click="closeCreateDialog()" text> Cancel </v-btn>
                  <v-btn
                    color="info"
                    @click="saveFilter()"
                    :loading="loading"
                    :disabled="invalid || !validated"
                  >
                    Save
                  </v-btn>
                </v-card-actions>
              </v-card>
            </ValidationObserver>
          </v-stepper-content>
        </v-stepper-items>
      </v-stepper>
    </v-card>
  </v-dialog>
</template>

<script>
import { ValidationObserver, ValidationProvider, extend } from "vee-validate"
import { mapActions } from "vuex"
import { mapFields } from "vuex-map-fields"
import { required } from "vee-validate/dist/rules"

import CaseApi from "@/case/api"
import CasePriority from "@/case/priority/CasePriority.vue"
import CasePriorityCombobox from "@/case/priority/CasePriorityCombobox.vue"
import CaseStatus from "@/case/CaseStatus.vue"
import CaseStatusMultiSelect from "@/case/CaseStatusMultiSelect.vue"
import CaseTypeCombobox from "@/case/type/CaseTypeCombobox.vue"
import SearchUtils from "@/search/utils"
import TagFilterAutoComplete from "@/tag/TagFilterAutoComplete.vue"
import TagTypeFilterCombobox from "@/tag_type/TagTypeFilterCombobox.vue"

extend("required", {
  ...required,
  message: "This field is required",
})

export default {
  name: "CaseSearchFilterCreateDialog",
  props: {
    value: {
      type: Object,
      default: null,
    },
  },

  data() {
    return {
      visibilities: [{ name: "Open" }, { name: "Restricted" }],
      editorOptions: {
        automaticLayout: true,
        renderValidationDecorations: "on",
      },
      previewFields: [
        { text: "Name", value: "name", sortable: false },
        { text: "Title", value: "title", sortable: false },
        { text: "Status", value: "status", sortable: false },
        { text: "Case Type", value: "case_type.name", sortable: false },
        { text: "Case Priority", value: "case_priority.name", sortable: false },
      ],
      step: 1,
      previewRows: {
        items: [],
        total: null,
      },
      previewRowsLoading: false,
      searchFilter: {
        project: null,
        expression: null,
        description: null,
        name: null,
        subject: "Case",
        filters: {
          case_type: [],
          case_priority: [],
          status: [],
          tag: [],
          tag_type: [],
          visibility: [],
        },
      },
    }
  },
  components: {
    ValidationObserver,
    ValidationProvider,
    TagFilterAutoComplete,
    CaseTypeCombobox,
    CasePriorityCombobox,
    TagTypeFilterCombobox,
    CaseStatusMultiSelect,
    CaseStatus,
    CasePriority,
    MonacoEditor: () => import("monaco-editor-vue"),
  },
  computed: {
    ...mapFields("search", ["loading", "dialogs.showCreate"]),
    ...mapFields("route", ["query"]),
    expression_str: {
      get: function () {
        return JSON.stringify(this.searchFilter.expression, null, "\t") || "[]"
      },
      set: function (newValue) {
        this.searchFilter.expression = JSON.parse(newValue)
      },
    },
  },

  methods: {
    ...mapActions("search", ["closeCreateDialog", "save"]),

    saveFilter() {
      // reset local data
      this.save(this.searchFilter).then((filter) => {
        this.$emit("input", filter)
      })
    },

    getPreviewData() {
      let params = {}
      if (this.expression) {
        params = { filter: JSON.stringify(this.expression) }
        this.previewRowsLoading = "error"
      }
      return CaseApi.getAll(params).then((response) => {
        this.previewRows = response.data
        this.previewRowsLoading = false
      })
    },
  },
  created() {
    if (this.query.project) {
      this.searchFilter.project = { name: this.query.project }
    }
    this.getPreviewData()
    this.$watch(
      (vm) => [
        vm.searchFilter.filters.case_type,
        vm.searchFilter.filters.case_priority,
        vm.searchFilter.filters.status,
        vm.searchFilter.filters.tag,
        vm.searchFilter.filters.tag_type,
        vm.searchFilter.filters.visibility,
      ],
      () => {
        this.searchFilter.expression = SearchUtils.createFilterExpression(this.searchFilter.filters)
        this.getPreviewData()
      }
    )
  },
}
</script>
