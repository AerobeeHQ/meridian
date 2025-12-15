# Issue 007: Adobe Analytics 2.0 API Migration Plan

**Date:** December 15, 2024  
**Type:** Documentation / Planning  
**Status:** Completed

## Objective

Create a comprehensive migration plan for transitioning the Codex application from Adobe Analytics API 1.4 (WSSE authentication) to Adobe Analytics API 2.0 (OAuth2 authentication). The plan must be detailed enough to be assigned to GitHub Copilot for implementation.

## Problem Statement

The application currently uses Adobe Analytics API 1.4 with legacy WSSE authentication. As Adobe phases out the 1.4 API, the application needs to migrate to the 2.0 API which uses modern OAuth2/JWT authentication. The migration requires:

1. Understanding Adobe I/O Console project setup
2. Configuring OAuth2 credentials and authentication
3. Evaluating available Python packages
4. Mapping 1.4 API endpoints to 2.0 equivalents
5. Planning code changes required for migration

## Investigation

### Current Implementation Analysis

**Files Examined:**
- `/app/services/adobe_analytics.py` - Current 1.4 API service with WSSE authentication
- `/app/routes/main.py` - Route handlers using the API service
- `/docs/adobe_analytics_api_1.4_swagger.json` - 1.4 API specification
- `/docs/adobe_analytics_api_2.0_swagger.json` - 2.0 API specification
- `/config.dist.json` - Current configuration format
- `/requirements.txt` - Current dependencies

**Current API Methods Used:**
1. `Company.GetReportSuites` - List report suites
2. `ReportSuite.GetProps` - Get traffic variables (props)
3. `ReportSuite.GetEvars` - Get conversion variables (eVars)
4. `ReportSuite.GetEvents` - Get success events
5. `ReportSuite.GetListVariables` - Get list variables
6. `ReportSuite.ViewProcessingRules` - Get processing rules
7. `ReportSuite.GetMarketingChannels` - Get marketing channels
8. `ReportSuite.GetMarketingChannelRules` - Get channel rules

**Authentication:**
- Current: WSSE (username + shared secret)
- Target: OAuth2 server-to-server or JWT

### Python Package Evaluation

**Packages Reviewed:**

1. **aanalytics2** (https://github.com/pitchmuc/aanalytics2)
   - Full 2.0 API support
   - OAuth2 and JWT authentication
   - Active maintenance
   - Community adoption
   - Additional dependencies

2. **Direct API Implementation** (Current approach)
   - No external dependencies (beyond `requests`)
   - Full control over behavior
   - Consistent with current architecture
   - More code to maintain

**Recommendation:** Continue with direct API implementation for consistency, control, and security.

### API Mapping Challenges

**Key Findings:**

1. **Processing Rules Not Available in 2.0 API**
   - No public endpoint for processing rules in 2.0 API
   - **Solution:** Maintain hybrid approach (1.4 for processing rules, 2.0 for everything else)

2. **Response Structure Changes**
   - 2.0 API uses different response format (pagination, nested objects)
   - eVar/prop data may require multiple API calls for full details
   - Need transformation layer to maintain compatibility

3. **Authentication Complexity**
   - OAuth2 requires token management and refresh
   - Need to implement token caching
   - JWT requires certificate management (optional approach)

## Solution

### Deliverable: `/docs/api-migration.md`

Created a comprehensive 1,380-line migration plan document covering:

#### 1. Adobe I/O Console Project Setup
- Step-by-step instructions for creating project
- OAuth2 vs JWT authentication options
- Product profile configuration
- Credential gathering checklist

#### 2. Credentials & OAuth Setup
- Configuration file structure
- Token acquisition flows (OAuth2 and JWT)
- Token caching strategy
- Security best practices

#### 3. Python Package Review
- Evaluation of `aanalytics2` package
- Comparison matrix (package vs direct API)
- Pros and cons analysis

#### 4. Recommendation
- **Recommendation:** Direct API implementation
- **Rationale:** Consistency, control, security, simplicity
- Implementation strategy with phases
- Fallback option if complexity increases

#### 5. API 1.4 to 2.0 Mapping
- Authentication mapping (WSSE → OAuth2)
- Endpoint mapping table (8 methods)
- Processing rules gap analysis
- Request/response structure changes
- Data model mapping examples

#### 6. High-Level Code Changes
- New files to create:
  - `app/services/adobe_auth.py` (OAuth2/JWT authentication)
  - `app/services/adobe_analytics_v2.py` (2.0 API service)
- Files to modify:
  - `config.dist.json` (new OAuth2 fields)
  - `app/routes/main.py` (service initialization)
  - `requirements.txt` (PyJWT, cryptography)
  - Documentation files
- Complete code examples:
  - OAuth2 authentication class (100+ lines)
  - Analytics 2.0 service class (100+ lines)
  - Configuration updates
  - Route updates

#### 7. Additional Sections
- Testing strategy (unit, integration, manual)
- Risk analysis (high, medium, low risk items)
- 6-week timeline estimate with phases
- Success criteria (functional & non-functional)
- Rollback plan
- Post-migration checklist
- Resources & references
- Questions & decisions log
- GitHub Copilot task breakdown

#### Appendices
- API response examples (1.4 vs 2.0)
- Error handling examples
- Glossary of terms

### Key Features of the Plan

1. **Actionable and Detailed**
   - Each section has clear steps
   - Code examples are copy-paste ready
   - Configuration examples are complete

2. **GitHub Copilot Ready**
   - Section 15.2 breaks down into 6 discrete tasks
   - Each task has clear inputs and outputs
   - Can be assigned sequentially to Copilot

3. **Risk-Aware**
   - Identifies processing rules gap
   - Proposes hybrid 1.4 + 2.0 approach
   - Includes rollback strategy

4. **Complete Coverage**
   - All 8 current API methods mapped
   - Authentication fully specified
   - Configuration changes documented
   - Testing strategy included

## Technical Decisions

### 1. Direct API vs Python Package
**Decision:** Use direct API implementation  
**Rationale:**
- Consistency with current architecture
- Full control over authentication and error handling
- No additional dependencies
- Smaller security surface area
- MVP velocity principle

### 2. OAuth2 vs JWT Authentication
**Decision:** Recommend OAuth2 Server-to-Server (with JWT as option)  
**Rationale:**
- OAuth2 is Adobe's recommended approach
- No certificate management required
- Simpler implementation
- Automatic token refresh

### 3. Processing Rules Handling
**Decision:** Hybrid approach (1.4 + 2.0)  
**Rationale:**
- Processing rules not available in 2.0 API
- Maintain 1.4 authentication for this endpoint only
- Preserve critical functionality
- Wait for Adobe to provide 2.0 equivalent

### 4. Migration Strategy
**Decision:** Gradual migration with feature flag  
**Rationale:**
- Reduce risk of breaking changes
- Allow endpoint-by-endpoint testing
- Enable quick rollback if needed
- Maintain production stability

## Implementation

### Files Created
1. **`/docs/api-migration.md`** (1,380 lines)
   - Complete migration guide
   - Ready for GitHub Copilot assignment
   - 15 main sections + 3 appendices

### Files Modified
None (documentation-only task as requested)

## Outcome

✅ **Success**

Created a comprehensive, production-ready migration plan that:

1. ✅ Describes Adobe I/O Console project setup steps in detail
2. ✅ Documents OAuth2/JWT credential setup and token management
3. ✅ Reviews available Python packages with detailed analysis
4. ✅ Recommends direct API implementation with clear rationale
5. ✅ Maps all 8 API 1.4 methods to 2.0 equivalents
6. ✅ Provides high-level code changes summary with examples
7. ✅ Formatted for GitHub Copilot task assignment
8. ✅ Includes timelines, risks, testing, and rollback plans

The plan is ready to be used as a blueprint for implementation, with each section detailed enough for assignment to GitHub Copilot or manual implementation.

## Key Insights

### What Went Well
1. **Comprehensive Research**
   - Analyzed both 1.4 and 2.0 API specifications
   - Reviewed current implementation thoroughly
   - Evaluated available Python packages

2. **Practical Approach**
   - Recommended direct API for consistency
   - Identified processing rules gap early
   - Proposed realistic hybrid solution

3. **GitHub Copilot Ready**
   - Clear task breakdown in Section 15.2
   - Code examples are complete and usable
   - Each section can be assigned independently

### Challenges Encountered

1. **Processing Rules Gap**
   - 2.0 API doesn't expose processing rules
   - Required fallback to hybrid approach
   - May need Adobe support for clarification

2. **Response Structure Differences**
   - 2.0 API has different data models
   - Some eVar/prop metadata may require additional calls
   - Transformation layer needed

3. **Documentation Scope**
   - Balancing detail vs readability
   - Ensuring all use cases covered
   - Making it Copilot-friendly

### Lessons Learned

1. **API Migration Complexity**
   - Authentication changes are non-trivial
   - Not all endpoints have 1:1 mappings
   - Need fallback strategies for gaps

2. **Documentation as Code**
   - Good plan structure enables automation
   - Code examples accelerate implementation
   - Clear task breakdown is essential

3. **Pragmatism Over Perfection**
   - Hybrid approach is acceptable
   - Direct API better than "perfect" library
   - MVP velocity guides decisions

## Next Steps

For the product owner/development team:

1. **Review Migration Plan**
   - Read `/docs/api-migration.md`
   - Validate approach and timeline
   - Identify any missing requirements

2. **Create Adobe I/O Project**
   - Follow Section 1 of migration plan
   - Gather OAuth2 credentials
   - Test API access in console

3. **Assign to GitHub Copilot**
   - Use Section 15.2 task breakdown
   - Start with Task 1: OAuth2 Authentication
   - Progress through 6 phases

4. **Address Open Questions**
   - Processing rules API availability
   - Permission requirements
   - Backward compatibility needs

5. **Plan Implementation Sprint**
   - Allocate 6 weeks for migration
   - Set up test environment
   - Plan rollback procedures

## References

- **Migration Plan:** `/docs/api-migration.md`
- **Current Service:** `/app/services/adobe_analytics.py`
- **1.4 API Spec:** `/docs/adobe_analytics_api_1.4_swagger.json`
- **2.0 API Spec:** `/docs/adobe_analytics_api_2.0_swagger.json`
- **Adobe Analytics 2.0 API Guide:** https://developer.adobe.com/analytics-apis/docs/2.0/
- **Adobe I/O Console:** https://console.adobe.io/
- **aanalytics2 Package:** https://github.com/pitchmuc/aanalytics2

---

**Status:** Plan complete and ready for implementation  
**Estimated Implementation Time:** 6 weeks (with team)  
**Risk Level:** Medium (Processing rules gap identified and mitigated)
