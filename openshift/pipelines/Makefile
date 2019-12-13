OC:=oc
OCFLAGS:=
JOBS_DIR:=jobs
TEMPLATES_DIR:=templates
JOB_PARAM_FILES:=$(wildcard $(JOBS_DIR)/*.env)
JOBS:=$(patsubst $(JOBS_DIR)/%.env,%,$(JOB_PARAM_FILES))

OC_CMD=$(OC) $(OCFLAGS)

help:
	@echo TARGETS
	@echo -e "\tinstall\t\tInstall or update pipelines to OpenShift"
	@echo -e "\tuninstall\tDelete installed pipelines from OpenShift"
	@echo
	@echo VARIABLES
	@echo -e "\tJOBS\t\tSpace seperated list of pipeline jobs to install"
	@echo -e "\tJOBS_DIR\tLooking for pipeline job definitions in an alternate directory."
	@echo -e "\tTEMPLATES_DIR\tLooking for pipeline job templates in an alternate directory."
	@echo -e "\tOC\t\tUse this oc command"
	@echo -e "\tOCFLAGS\t\tOptions to append to the oc command arguments"
install:
	@for job in $(JOBS); do \
		echo "[PIPELINE] Updating pipeline job \"$${job}\"..." ; \
	  template_file=$$(cat ./$(JOBS_DIR)/$${job}.tmpl); \
		jinja2 ./$(TEMPLATES_DIR)/$${template_file} | $(OC_CMD) process --local -f - \
			--param-file ./$(JOBS_DIR)/$${job}.env | $(OC_CMD) apply -f -; \
		echo "[PIPELINE] Pipeline job \"$${job}\" updated" ; \
	done
uninstall:
	@for job in $(JOBS); do \
	  template_file=$$(cat ./$(JOBS_DIR)/$${job}.tmpl); \
		template_name=$${template_file%.y?ml}; \
		template_name=$${template_name%-template}; \
		echo "[PIPELINE] Deleting pipeline job \"$${job}\"..." ; \
		$(OC_CMD) delete all -l template="$$template_name" -l app="$$job" ;\
		echo "[PIPELINE] Pipeline job \"$${job}\" deleted" ; \
	done
.PHONY: help install uninstall
