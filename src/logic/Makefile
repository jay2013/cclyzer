# Directory depth
LEVEL := ../..

# Placeholder
all:

# Import common Makefile routines
include $(LEVEL)/src/common.mk
include blox.mk

# Generate build directory for logic
$(eval $(call create-destdir,logic))

# Projects (add directory here to enable it)
projects      := schema import symbol-lookup callgraph
project.files := $(shell find -type f -name '*.project')


#-----------------------------------
# Phony targets
#-----------------------------------

all:

force:

clean:
	$(RM) -r $(logic.outdir)

.PHONY: all clean install uninstall force


#------------------------------
#  Project Creation Template
#------------------------------

define project_template

$1.proj   := $1/$1.project
$1.src    := $(wildcard $1/*.logic)
$1.outdir := $(logic.outdir)/$1
$1.ph     := $$($1.outdir)/.placeholder
$1.deps   := $1/deps.mk


# Create output directory
$$($1.outdir): | $(logic.outdir)
	$(MKDIR) $$@

# Auto-generate project dependencies
export PATH := $(LEVEL)/bin:$(PATH)
$$($1.deps): $$($1.proj) | $$($1.outdir)
	project-dependencies.sh . $$< $$($1.ph) > $$@


# When a single `.project' file changes, *all* project-dependency
# Makefile modules must be renewed, since their generation involves
# reading all `.project' files to acquire their /project IDs/.

$$($1.deps): $(project.files)


# Include deps.mk Makefile segment
-include $$($1.deps)


# Compile project
$$($1.ph): $$($1.proj) $$($1.src) | $$($1.outdir)
	$(call compile-datalog-project, $$<,$$(@D))
	$(QUIET) touch $$@


# Project build target
.PHONY: $1
$1: $$($1.ph)

# Project clean targets
.PHONY: $1.clean
$1.clean:
	$(RM) -r $$($1.outdir)

.PHONY: $1.clean-deps
$1.clean-deps:
	$(RM) $$($1.deps)

.PHONY: $1.cleanall
$1.cleanall: $1.clean $1.clean-deps

# Phony target dependencies
all:        $1
clean:      $1.clean
clean-deps: $1.clean-deps
cleanall:   $1.cleanall

endef

# !! Generate rules per project !!
$(foreach project,$(projects),$(eval $(call project_template,$(project))))


#------------------------------------------------------------------------------
#  [Generate Import Sources]
#
#   When the schema changes, it is often necessary to regenerate the
#   import logic. The steps are the following:
#
#     i. make sure that PATH contains the import-generator binary
#    ii. run the `import.src' target of this Makefile
#
#   TODO add the above instructions on the project's README
#------------------------------------------------------------------------------

schema.pb   := $(schema.src:schema/%.logic=$(import.outdir)/%.pb)
export PATH := $(INSTALL_BIN):$(LEVEL)/bin:$(PATH)

# Generate protobuf messages from schema
.INTERMEDIATE: $(schema.pb)
$(schema.pb): $(import.outdir)/%.pb: $(schema.ph) | $(import.outdir)
	$(call generate-protobuf-message,$(schema.outdir)/$*.lbb,$@)

# Generate import sources; this will recreate $(import.src) files
.PHONY: import.src
import.src: $(schema.pb)
	$(importgen.exe) --ignore import/.ignored-predicates --dir facts --delim '\t' -o import $^